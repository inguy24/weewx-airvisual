#!/usr/bin/env python3

"""
Unit Test Suite for WeeWX AirVisual Extension

This test suite validates the AirVisual service functionality including:
- API client operations
- Data parsing and validation
- Retry logic
- Configuration handling
- Database integration

Run with: python3 -m pytest test_airvisual.py -v
Or: python3 test_airvisual.py
"""

import json
import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys

# Add the parent directory to sys.path to import airvisual module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bin', 'user'))

try:
    import airvisual
except ImportError:
    print("❌ Cannot import airvisual module. Ensure bin/user/airvisual.py exists.")
    sys.exit(1)


class TestAirVisualService(unittest.TestCase):
    """Test the main AirVisualService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_engine = Mock()
        self.mock_engine.config_dict = {
            'Station': {
                'latitude': 33.656915,
                'longitude': -117.982542
            },
            'AirVisualService': {
                'enable': True,
                'api_key': 'test_api_key_123',
                'interval': 600,
                'timeout': 30,
                'log_success': False,
                'log_errors': True,
                'retry_wait_base': 600,
                'retry_wait_max': 21600,
                'retry_multiplier': 2.0
            }
        }
    
    def test_configuration_parsing(self):
        """Test configuration parsing from weewx.conf."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # Verify configuration was parsed correctly
            self.assertEqual(service.config['api_key'], 'test_api_key_123')
            self.assertEqual(service.config['latitude'], 33.656915)
            self.assertEqual(service.config['longitude'], -117.982542)
            self.assertEqual(service.config['interval'], 600)
            self.assertTrue(service.config['enable'])
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Test missing API key
        invalid_config = self.mock_engine.config_dict.copy()
        invalid_config['AirVisualService']['api_key'] = ''
        
        with patch('airvisual.log'), \
             self.assertRaises(Exception):  # Should raise ViolatedPrecondition
            airvisual.AirVisualService(self.mock_engine, invalid_config)
    
    def test_coordinate_validation(self):
        """Test coordinate validation."""
        # Test invalid latitude
        invalid_config = self.mock_engine.config_dict.copy()
        invalid_config['Station']['latitude'] = 91.0  # Invalid latitude
        
        with patch('airvisual.log'), \
             self.assertRaises(Exception):
            airvisual.AirVisualService(self.mock_engine, invalid_config)
        
        # Test invalid longitude
        invalid_config = self.mock_engine.config_dict.copy()
        invalid_config['Station']['longitude'] = 181.0  # Invalid longitude
        
        with patch('airvisual.log'), \
             self.assertRaises(Exception):
            airvisual.AirVisualService(self.mock_engine, invalid_config)
    
    def test_disabled_service(self):
        """Test service when disabled in configuration."""
        disabled_config = self.mock_engine.config_dict.copy()
        disabled_config['AirVisualService']['enable'] = False
        
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, disabled_config)
            
            # Service should not start background thread when disabled
            self.assertIsNone(service.api_thread)


class TestAPIResponseParsing(unittest.TestCase):
    """Test API response parsing and validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_engine = Mock()
        self.mock_engine.config_dict = {
            'Station': {'latitude': 33.656915, 'longitude': -117.982542},
            'AirVisualService': {
                'enable': True,
                'api_key': 'test_key',
                'interval': 600,
                'timeout': 30,
                'log_success': False,
                'log_errors': True
            }
        }
    
    def test_valid_api_response(self):
        """Test parsing of valid API response."""
        valid_response = {
            "status": "success",
            "data": {
                "city": "Huntington Beach",
                "state": "California",
                "country": "USA",
                "current": {
                    "pollution": {
                        "ts": "2025-01-07T12:00:00.000Z",
                        "aqius": 42,
                        "mainus": "p2"
                    }
                }
            }
        }
        
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            result = service._parse_api_response(valid_response)
            
            self.assertIsNotNone(result)
            self.assertEqual(result['aqi'], 42)
            self.assertEqual(result['main_pollutant'], 'PM2.5')
            self.assertEqual(result['aqi_level'], 'Good')
    
    def test_invalid_api_response_status(self):
        """Test parsing of API response with error status."""
        error_response = {
            "status": "error",
            "data": "Invalid API key"
        }
        
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            result = service._parse_api_response(error_response)
            
            self.assertIsNone(result)
    
    def test_missing_pollution_data(self):
        """Test parsing of response missing pollution data."""
        incomplete_response = {
            "status": "success",
            "data": {
                "city": "Test City",
                "current": {}  # Missing pollution data
            }
        }
        
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            result = service._parse_api_response(incomplete_response)
            
            self.assertIsNone(result)
    
    def test_invalid_aqi_values(self):
        """Test parsing of response with invalid AQI values."""
        invalid_responses = [
            # Missing aqius
            {
                "status": "success",
                "data": {
                    "current": {
                        "pollution": {
                            "mainus": "p2"
                        }
                    }
                }
            },
            # Negative AQI
            {
                "status": "success",
                "data": {
                    "current": {
                        "pollution": {
                            "aqius": -5,
                            "mainus": "p2"
                        }
                    }
                }
            },
            # Non-numeric AQI
            {
                "status": "success",
                "data": {
                    "current": {
                        "pollution": {
                            "aqius": "invalid",
                            "mainus": "p2"
                        }
                    }
                }
            }
        ]
        
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            for response in invalid_responses:
                result = service._parse_api_response(response)
                self.assertIsNone(result, f"Should reject invalid response: {response}")


class TestRetryLogic(unittest.TestCase):
    """Test exponential backoff retry logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_engine = Mock()
        self.mock_engine.config_dict = {
            'Station': {'latitude': 33.656915, 'longitude': -117.982542},
            'AirVisualService': {
                'enable': True,
                'api_key': 'test_key',
                'interval': 600,
                'timeout': 30,
                'retry_wait_base': 60,  # Shorter for testing
                'retry_wait_max': 300,  # Shorter for testing
                'retry_multiplier': 2.0,
                'log_errors': False  # Reduce test noise
            }
        }
    
    def test_retry_state_initialization(self):
        """Test retry state is properly initialized."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            self.assertEqual(service.retry_state['consecutive_failures'], 0)
            self.assertEqual(service.retry_state['current_wait_time'], 60)
            self.assertIsNone(service.retry_state['last_success_time'])
    
    def test_retry_state_reset_on_success(self):
        """Test retry state resets after successful API call."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # Simulate some failures
            service.retry_state['consecutive_failures'] = 3
            service.retry_state['current_wait_time'] = 240
            
            # Reset on success
            service._reset_retry_state()
            
            self.assertEqual(service.retry_state['consecutive_failures'], 0)
            self.assertEqual(service.retry_state['current_wait_time'], 60)
            self.assertIsNotNone(service.retry_state['last_success_time'])
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # Test progression: 60 -> 120 -> 240 -> 300 (max)
            expected_waits = [60, 120, 240, 300, 300]  # Caps at 300
            
            for i, expected_wait in enumerate(expected_waits):
                current_time = time.time()
                service._handle_api_failure()
                
                self.assertEqual(service.retry_state['consecutive_failures'], i + 1)
                actual_wait = service.retry_state['next_retry_time'] - current_time
                self.assertAlmostEqual(actual_wait, expected_wait, delta=1.0)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions for data conversion."""
    
    def test_aqi_to_level_conversion(self):
        """Test AQI numeric to level conversion."""
        test_cases = [
            (25, "Good"),
            (50, "Good"),
            (75, "Moderate"),
            (100, "Moderate"),
            (125, "Unhealthy for Sensitive Groups"),
            (150, "Unhealthy for Sensitive Groups"),
            (175, "Unhealthy"),
            (200, "Unhealthy"),
            (250, "Very Unhealthy"),
            (300, "Very Unhealthy"),
            (350, "Hazardous"),
            (500, "Hazardous"),
            (None, None)
        ]
        
        for aqi, expected_level in test_cases:
            result = airvisual.convert_aqi_to_level(aqi)
            self.assertEqual(result, expected_level, f"AQI {aqi} should be {expected_level}")
    
    def test_pollutant_code_conversion(self):
        """Test pollutant code to name conversion."""
        test_cases = [
            ('p2', 'PM2.5'),
            ('p1', 'PM10'),
            ('o3', 'Ozone'),
            ('n2', 'NO2'),
            ('s2', 'SO2'),
            ('co', 'CO'),
            ('unknown', 'unknown'),  # Unknown codes pass through
            (None, None)
        ]
        
        for code, expected_name in test_cases:
            result = airvisual.convert_pollutant_code(code)
            self.assertEqual(result, expected_name, f"Code {code} should be {expected_name}")


class TestThreadSafety(unittest.TestCase):
    """Test thread-safe operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_engine = Mock()
        self.mock_engine.config_dict = {
            'Station': {'latitude': 33.656915, 'longitude': -117.982542},
            'AirVisualService': {
                'enable': False,  # Don't start background thread
                'api_key': 'test_key',
                'interval': 600,
                'timeout': 30
            }
        }
    
    def test_data_lock_usage(self):
        """Test that data access uses proper locking."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # Test data writing with lock
            test_data = {'aqi': 42, 'main_pollutant': 'PM2.5', 'timestamp': time.time()}
            with service.data_lock:
                service.latest_data = test_data
            
            # Test data reading with lock
            with service.data_lock:
                retrieved_data = service.latest_data.copy()
            
            self.assertEqual(retrieved_data['aqi'], 42)
            self.assertEqual(retrieved_data['main_pollutant'], 'PM2.5')
    
    def test_concurrent_data_access(self):
        """Test concurrent data access safety."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            results = []
            errors = []
            
            def writer_thread():
                try:
                    for i in range(10):
                        with service.data_lock:
                            service.latest_data = {'aqi': i, 'timestamp': time.time()}
                        time.sleep(0.001)  # Small delay
                except Exception as e:
                    errors.append(e)
            
            def reader_thread():
                try:
                    for i in range(10):
                        with service.data_lock:
                            data = service.latest_data.copy()
                        results.append(data.get('aqi'))
                        time.sleep(0.001)  # Small delay
                except Exception as e:
                    errors.append(e)
            
            # Start concurrent threads
            threads = []
            for _ in range(2):
                threads.append(threading.Thread(target=writer_thread))
                threads.append(threading.Thread(target=reader_thread))
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join(timeout=5)
            
            # No errors should occur with proper locking
            self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")


class TestArchiveRecordInjection(unittest.TestCase):
    """Test injection of air quality data into archive records."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_engine = Mock()
        self.mock_engine.config_dict = {
            'Station': {'latitude': 33.656915, 'longitude': -117.982542},
            'AirVisualService': {
                'enable': False,  # Don't start background thread
                'api_key': 'test_key',
                'interval': 600,
                'timeout': 30,
                'log_success': False
            }
        }
    
    def test_fresh_data_injection(self):
        """Test injection of fresh air quality data."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # Set up fresh data
            fresh_data = {
                'aqi': 42,
                'main_pollutant': 'PM2.5',
                'aqi_level': 'Good',
                'timestamp': time.time()
            }
            
            with service.data_lock:
                service.latest_data = fresh_data
            
            # Create mock event
            mock_event = Mock()
            mock_event.record = {}
            
            # Call injection method
            service.new_archive_record(mock_event)
            
            # Verify data was injected
            self.assertEqual(mock_event.record['aqi'], 42)
            self.assertEqual(mock_event.record['main_pollutant'], 'PM2.5')
            self.assertEqual(mock_event.record['aqi_level'], 'Good')
    
    def test_stale_data_handling(self):
        """Test handling of stale air quality data."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # Set up stale data (older than 2 intervals)
            stale_data = {
                'aqi': 42,
                'main_pollutant': 'PM2.5',
                'aqi_level': 'Good',
                'timestamp': time.time() - 1300  # > 2 * 600 seconds
            }
            
            with service.data_lock:
                service.latest_data = stale_data
            
            # Create mock event
            mock_event = Mock()
            mock_event.record = {}
            
            # Call injection method
            service.new_archive_record(mock_event)
            
            # Verify stale data was not injected (set to None)
            self.assertIsNone(mock_event.record['aqi'])
            self.assertIsNone(mock_event.record['main_pollutant'])
            self.assertIsNone(mock_event.record['aqi_level'])
    
    def test_no_data_handling(self):
        """Test handling when no air quality data is available."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # No data available (empty dict)
            with service.data_lock:
                service.latest_data = {}
            
            # Create mock event
            mock_event = Mock()
            mock_event.record = {}
            
            # Call injection method
            service.new_archive_record(mock_event)
            
            # Verify None values were set
            self.assertIsNone(mock_event.record['aqi'])
            self.assertIsNone(mock_event.record['main_pollutant'])
            self.assertIsNone(mock_event.record['aqi_level'])


class TestServiceShutdown(unittest.TestCase):
    """Test service shutdown behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_engine = Mock()
        self.mock_engine.config_dict = {
            'Station': {'latitude': 33.656915, 'longitude': -117.982542},
            'AirVisualService': {
                'enable': False,  # Don't auto-start thread
                'api_key': 'test_key',
                'interval': 600,
                'timeout': 30
            }
        }
    
    def test_clean_shutdown(self):
        """Test clean shutdown of the service."""
        with patch('airvisual.log'):
            service = airvisual.AirVisualService(self.mock_engine, self.mock_engine.config_dict)
            
            # Manually create and start a thread for testing
            service.api_thread = threading.Thread(
                target=lambda: time.sleep(0.1),  # Short-lived thread
                daemon=True
            )
            service.api_thread.start()
            
            # Verify thread is alive
            self.assertTrue(service.api_thread.is_alive())
            
            # Call shutdown
            service.shutDown()
            
            # Verify shutdown event was set
            self.assertTrue(service.shutdown_event.is_set())
            
            # Wait for thread to finish
            service.api_thread.join(timeout=1)
            self.assertFalse(service.api_thread.is_alive())


def run_tests():
    """Run all tests."""
    print("WeeWX AirVisual Extension - Unit Test Suite")
    print("=" * 50)
    
    # Create test suite
    test_classes = [
        TestAirVisualService,
        TestAPIResponseParsing,
        TestRetryLogic,
        TestUtilityFunctions,
        TestThreadSafety,
        TestArchiveRecordInjection,
        TestServiceShutdown
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nResult: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
