#!/usr/bin/env python3

"""
WeeWX AirVisual Service Plugin

This service integrates IQ Air's AirVisual API to collect air quality data 
and inject it into WeeWX's data pipeline. Features include:

- Reads station coordinates from existing WeeWX configuration
- Exponential backoff retry logic with indefinite retries  
- Thread-safe background data collection
- Proper WeeWX extension integration
- Full HTTP client with comprehensive error handling

Copyright (c) 2025
Distributed under the terms of the GNU Public License (GPLv3)
"""

import json
import logging
import threading
import time
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from socket import timeout as socket_timeout

import weewx
from weewx.engine import StdService
import weewx.units

# Set up logging
log = logging.getLogger(__name__)

# Extension version
VERSION = "1.0.0"

# Unit system setup for AQI data
weewx.units.obs_group_dict['aqi'] = 'group_aqi'
weewx.units.obs_group_dict['main_pollutant'] = 'group_count'
weewx.units.obs_group_dict['aqi_level'] = 'group_count'

# Unit definitions for all unit systems
weewx.units.USUnits['group_aqi'] = 'aqi'
weewx.units.MetricUnits['group_aqi'] = 'aqi'  
weewx.units.MetricWXUnits['group_aqi'] = 'aqi'

# Display formatting
weewx.units.default_unit_format_dict['aqi'] = '%.0f'
weewx.units.default_unit_label_dict['aqi'] = ' AQI'


class AirVisualService(StdService):
    """
    WeeWX service to collect air quality data from IQ Air's AirVisual API.
    
    Features:
    - Uses station coordinates from [Station] section
    - Exponential backoff retry with indefinite attempts
    - Thread-safe background data collection
    - Graceful error handling without data gaps
    - Full HTTP client with comprehensive error handling
    """
    
    def __init__(self, engine, config_dict):
        """Initialize the AirVisual service."""
        super(AirVisualService, self).__init__(engine, config_dict)
        
        log.info(f"AirVisual service version {VERSION} starting")
        
        # Parse configuration from weewx.conf
        self.config = self._parse_config(config_dict)
        
        # Validate configuration
        self._validate_config()
        
        # Thread-safe data storage
        self.data_lock = threading.Lock()
        self.latest_data: Dict[str, Any] = {}
        
        # Retry state management
        self.retry_state = {
            'consecutive_failures': 0,
            'next_retry_time': 0,
            'current_wait_time': self.config['retry_wait_base'],
            'last_success_time': None
        }
        
        # Background thread management
        self.api_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        # Start background data collection if enabled
        if self.config['enable']:
            self._start_background_thread()
        
        # Bind to archive record events
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        
        log.info("AirVisual service initialized successfully")
    
    def _parse_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Parse configuration from weewx.conf."""
        
        # Get service-specific configuration
        service_config = config_dict.get('AirVisualService', {})
        
        # Get station coordinates from [Station] section (not duplicated)
        station_config = config_dict.get('Station', {})
        latitude = float(station_config.get('latitude', 0.0))
        longitude = float(station_config.get('longitude', 0.0))
        
        # Build configuration with defaults
        config = {
            'enable': service_config.get('enable', True),
            'api_key': service_config.get('api_key', ''),
            'latitude': latitude,
            'longitude': longitude,
            'interval': int(service_config.get('interval', 600)),  # 10 minutes
            'timeout': int(service_config.get('timeout', 30)),
            'log_success': service_config.get('log_success', False),
            'log_errors': service_config.get('log_errors', True),
            
            # Exponential backoff retry configuration
            'retry_wait_base': int(service_config.get('retry_wait_base', 600)),      # 10 minutes
            'retry_wait_max': int(service_config.get('retry_wait_max', 21600)),     # 6 hours max
            'retry_multiplier': float(service_config.get('retry_multiplier', 2.0)) # Double each time
        }
        
        log.debug(f"Parsed configuration: {config}")
        return config
    
    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        if not self.config['enable']:
            log.info("AirVisual service is disabled in configuration")
            return
        
        # Validate required API key
        if not self.config['api_key']:
            raise weewx.ViolatedPrecondition(
                "AirVisual service: api_key is required but not provided. "
                "Run 'weectl extension install airvisual.zip' to configure."
            )
        
        # Validate coordinates from [Station] section
        if not -90 <= self.config['latitude'] <= 90:
            raise weewx.ViolatedPrecondition(
                f"AirVisual service: Invalid latitude {self.config['latitude']} "
                "in [Station] section (must be between -90 and 90)"
            )
        
        if not -180 <= self.config['longitude'] <= 180:
            raise weewx.ViolatedPrecondition(
                f"AirVisual service: Invalid longitude {self.config['longitude']} "
                "in [Station] section (must be between -180 and 180)"
            )
        
        # Validate coordinates are not zero (likely not configured)
        if self.config['latitude'] == 0.0 and self.config['longitude'] == 0.0:
            raise weewx.ViolatedPrecondition(
                "AirVisual service: Station coordinates not configured. "
                "Please set latitude and longitude in [Station] section of weewx.conf"
            )
        
        # Warn about short intervals
        if self.config['interval'] < 300:  # 5 minutes
            log.warning(
                f"AirVisual service: interval {self.config['interval']} seconds "
                "is very short and may quickly exhaust API quota (10,000 calls/month)"
            )
        
        log.info(
            f"AirVisual service configured: "
            f"lat={self.config['latitude']}, lon={self.config['longitude']}, "
            f"interval={self.config['interval']}s"
        )
    
    def _start_background_thread(self):
        """Start the background thread for API data collection."""
        if self.api_thread is None or not self.api_thread.is_alive():
            self.api_thread = threading.Thread(
                target=self._api_collection_loop,
                name='AirVisualAPI',
                daemon=True
            )
            self.api_thread.start()
            log.info("Started AirVisual API collection thread")
    
    def _api_collection_loop(self):
        """
        Background thread loop for collecting API data.
        
        Implements exponential backoff retry logic:
        - Normal operation: collect every 'interval' seconds
        - On failure: wait increasingly longer between retries
        - On success after failures: reset to normal interval
        - Never give up - keeps retrying indefinitely
        """
        log.info("AirVisual API collection thread started")
        
        while not self.shutdown_event.is_set():
            try:
                current_time = time.time()
                
                # Check if we're in a retry backoff period
                if current_time < self.retry_state['next_retry_time']:
                    # Still waiting for retry time - sleep and continue
                    sleep_time = min(60, self.retry_state['next_retry_time'] - current_time)
                    if self.shutdown_event.wait(sleep_time):
                        break  # Shutdown requested
                    continue
                
                # Time to attempt data collection
                log.debug("Attempting to collect air quality data")
                
                # Collect air quality data from API
                success = self._collect_air_quality_data()
                
                if success:
                    # Success - reset retry state and use normal interval
                    if self.retry_state['consecutive_failures'] > 0:
                        log.info(
                            f"AirVisual API connection restored after "
                            f"{self.retry_state['consecutive_failures']} failures"
                        )
                    
                    self._reset_retry_state()
                    next_collection = current_time + self.config['interval']
                    
                else:
                    # Failure - implement exponential backoff
                    self._handle_api_failure()
                    next_collection = self.retry_state['next_retry_time']
                
                # Sleep until next collection time
                sleep_time = next_collection - time.time()
                if sleep_time > 0:
                    if self.shutdown_event.wait(sleep_time):
                        break  # Shutdown requested
                
            except Exception as e:
                log.error(f"Unexpected error in API collection thread: {e}")
                # Treat unexpected errors as API failures
                self._handle_api_failure()
                if self.shutdown_event.wait(60):  # Wait 1 minute before retrying
                    break
        
        log.info("AirVisual API collection thread stopped")
    
    def _collect_air_quality_data(self) -> bool:
        """
        Collect air quality data from the IQ Air AirVisual API.
        
        Returns:
            bool: True if successful, False if failed
        """
        try:
            # Build API request URL
            api_url = "http://api.airvisual.com/v2/nearest_city"
            params = {
                'lat': self.config['latitude'],
                'lon': self.config['longitude'],
                'key': self.config['api_key']
            }
            
            # Construct full URL with parameters
            full_url = f"{api_url}?{urlencode(params)}"
            
            # Create request with proper headers
            request = Request(full_url)
            request.add_header('User-Agent', f'WeeWX-AirVisual/{VERSION}')
            request.add_header('Accept', 'application/json')
            
            log.debug(f"Requesting air quality data from IQ Air API")
            
            # Make HTTP request with timeout
            with urlopen(request, timeout=self.config['timeout']) as response:
                if response.status != 200:
                    if self.config['log_errors']:
                        log.error(f"API returned HTTP {response.status}")
                    return False
                
                # Read and parse JSON response
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)
            
            # Validate response structure and extract data
            air_quality_data = self._parse_api_response(data)
            if air_quality_data is None:
                return False
            
            # Store data thread-safely
            with self.data_lock:
                self.latest_data = air_quality_data
            
            if self.config['log_success']:
                log.info(
                    f"Collected air quality data: AQI={air_quality_data['aqi']}, "
                    f"pollutant={air_quality_data['main_pollutant']}, "
                    f"level={air_quality_data['aqi_level']}"
                )
            
            return True
            
        except HTTPError as e:
            # Handle specific HTTP error codes
            if e.code == 401:
                if self.config['log_errors']:
                    log.error("API authentication failed - check API key")
            elif e.code == 429:
                if self.config['log_errors']:
                    log.error("API rate limit exceeded - will retry with backoff")
            elif 500 <= e.code < 600:
                if self.config['log_errors']:
                    log.error(f"API server error (HTTP {e.code}) - will retry")
            else:
                if self.config['log_errors']:
                    log.error(f"API request failed with HTTP {e.code}")
            return False
            
        except URLError as e:
            # Handle network/DNS errors
            if self.config['log_errors']:
                log.error(f"Network error connecting to API: {e.reason}")
            return False
            
        except socket_timeout:
            # Handle request timeouts
            if self.config['log_errors']:
                log.error(f"API request timed out after {self.config['timeout']} seconds")
            return False
            
        except json.JSONDecodeError as e:
            # Handle invalid JSON responses
            if self.config['log_errors']:
                log.error(f"Invalid JSON response from API: {e}")
            return False
            
        except Exception as e:
            # Handle any other unexpected errors
            if self.config['log_errors']:
                log.error(f"Unexpected error collecting air quality data: {e}")
            return False
    
    def _parse_api_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse and validate API response data.
        
        Args:
            data: JSON response from IQ Air API
            
        Returns:
            Dict with parsed air quality data, or None if invalid
        """
        try:
            # Check response status
            if data.get('status') != 'success':
                if self.config['log_errors']:
                    log.error(f"API returned error status: {data.get('status')}")
                return None
            
            # Navigate to pollution data
            current_data = data.get('data', {})
            if not current_data:
                if self.config['log_errors']:
                    log.error("API response missing 'data' section")
                return None
            
            pollution_data = current_data.get('current', {}).get('pollution', {})
            if not pollution_data:
                if self.config['log_errors']:
                    log.error("API response missing pollution data")
                return None
            
            # Extract key fields (US standard only)
            aqius = pollution_data.get('aqius')
            mainus = pollution_data.get('mainus')
            
            # Validate AQI value
            if aqius is None:
                if self.config['log_errors']:
                    log.error("API response missing 'aqius' field")
                return None
            
            if not isinstance(aqius, (int, float)) or aqius < 0:
                if self.config['log_errors']:
                    log.error(f"Invalid AQI value: {aqius}")
                return None
            
            # Validate main pollutant code
            if mainus is None:
                if self.config['log_errors']:
                    log.error("API response missing 'mainus' field")
                return None
            
            valid_pollutants = ['p2', 'p1', 'o3', 'n2', 's2', 'co']
            if mainus not in valid_pollutants:
                if self.config['log_errors']:
                    log.warning(f"Unknown pollutant code: {mainus}")
            
            # Convert data to our format
            air_quality_data = {
                'aqi': int(aqius),
                'main_pollutant': convert_pollutant_code(mainus),
                'aqi_level': convert_aqi_to_level(aqius),
                'timestamp': time.time()
            }
            
            # Log location info for debugging (only on success)
            if self.config['log_success']:
                city = current_data.get('city', 'Unknown')
                state = current_data.get('state', 'Unknown')
                country = current_data.get('country', 'Unknown')
                log.debug(f"Data from: {city}, {state}, {country}")
            
            return air_quality_data
            
        except Exception as e:
            if self.config['log_errors']:
                log.error(f"Error parsing API response: {e}")
            return None
    
    def _reset_retry_state(self):
        """Reset retry state after successful API call."""
        self.retry_state.update({
            'consecutive_failures': 0,
            'current_wait_time': self.config['retry_wait_base'],
            'last_success_time': time.time()
        })
    
    def _handle_api_failure(self):
        """Handle API failure with exponential backoff."""
        self.retry_state['consecutive_failures'] += 1
        
        # Calculate next retry time with exponential backoff
        wait_time = min(
            self.retry_state['current_wait_time'],
            self.config['retry_wait_max']
        )
        
        self.retry_state['next_retry_time'] = time.time() + wait_time
        
        # Increase wait time for next failure (exponential backoff)
        self.retry_state['current_wait_time'] = min(
            self.retry_state['current_wait_time'] * self.config['retry_multiplier'],
            self.config['retry_wait_max']
        )
        
        if self.config['log_errors']:
            log.warning(
                f"AirVisual API failure #{self.retry_state['consecutive_failures']}. "
                f"Next retry in {wait_time//60:.0f} minutes ({wait_time} seconds)"
            )
    
    def new_archive_record(self, event):
        """Inject air quality data into archive records."""
        if not self.config['enable']:
            return
        
        try:
            # Get latest air quality data (thread-safe)
            with self.data_lock:
                air_data = self.latest_data.copy()
            
            if air_data:
                # Check data freshness (don't use stale data)
                data_age = time.time() - air_data.get('timestamp', 0)
                max_age = self.config['interval'] * 2  # Allow data up to 2 intervals old
                
                if data_age <= max_age:
                    # Inject fresh air quality data into the archive record
                    event.record['aqi'] = air_data.get('aqi')
                    event.record['main_pollutant'] = air_data.get('main_pollutant')
                    event.record['aqi_level'] = air_data.get('aqi_level')
                    
                    if self.config['log_success']:
                        log.info(
                            f"Injected air quality data: AQI={air_data.get('aqi')}, "
                            f"pollutant={air_data.get('main_pollutant')}, "
                            f"level={air_data.get('aqi_level')}"
                        )
                else:
                    # Data is too old - don't use it
                    event.record['aqi'] = None
                    event.record['main_pollutant'] = None
                    event.record['aqi_level'] = None
                    
                    log.debug(f"Air quality data too old ({data_age:.0f}s), not injecting")
            else:
                # No data available - set fields to None (preserves database integrity)
                event.record['aqi'] = None
                event.record['main_pollutant'] = None
                event.record['aqi_level'] = None
                
                log.debug("No air quality data available for archive record")
                
        except Exception as e:
            if self.config['log_errors']:
                log.error(f"Error injecting air quality data: {e}")
            # Always set fields to None on error to prevent WeeWX issues
            event.record['aqi'] = None
            event.record['main_pollutant'] = None
            event.record['aqi_level'] = None
    
    def shutDown(self):
        """Clean shutdown of the service."""
        log.info("AirVisual service shutting down")
        
        # Signal background thread to stop
        self.shutdown_event.set()
        
        # Wait for background thread to finish
        if self.api_thread and self.api_thread.is_alive():
            self.api_thread.join(timeout=10)
            if self.api_thread.is_alive():
                log.warning("Background thread did not shut down cleanly")
        
        log.info("AirVisual service shutdown complete")


def convert_aqi_to_level(aqi: Optional[float]) -> Optional[str]:
    """Convert numeric AQI value to descriptive level."""
    if aqi is None:
        return None
    
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def convert_pollutant_code(code: Optional[str]) -> Optional[str]:
    """Convert IQ Air pollutant codes to readable names."""
    if code is None:
        return None
    
    pollutant_map = {
        'p2': 'PM2.5',
        'p1': 'PM10', 
        'o3': 'Ozone',
        'n2': 'NO2',
        's2': 'SO2',
        'co': 'CO'
    }
    
    return pollutant_map.get(code, code)


# Test runner for development
if __name__ == '__main__':
    print(f"AirVisual Service v{VERSION} - Development Test")
    print("Testing utility functions:")
    
    # Test AQI conversion
    test_values = [25, 75, 125, 175, 250, 350]
    for aqi in test_values:
        level = convert_aqi_to_level(aqi)
        print(f"  AQI {aqi}: {level}")
    
    # Test pollutant codes
    test_codes = ['p2', 'p1', 'o3', 'n2', 's2', 'co', 'unknown']
    for code in test_codes:
        name = convert_pollutant_code(code)
        print(f"  Code '{code}': {name}")
