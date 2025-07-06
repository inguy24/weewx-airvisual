#!/usr/bin/env python3

"""
IQ Air API Test Script

This script tests the IQ Air API connection and response parsing
independently of WeeWX. Use this to validate your API key and
understand the current API response format.

Usage:
    python3 api_test.py YOUR_API_KEY LAT LON
    
Example:
    python3 api_test.py abc123def456 33.656915 -117.982542
"""

import json
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def test_api_connection(api_key, latitude, longitude):
    """Test IQ Air API connection and response parsing."""
    
    print("IQ Air API Test Script")
    print("=" * 50)
    print(f"API Key: {api_key[:8]}...")
    print(f"Coordinates: {latitude}, {longitude}")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Build API request URL
    api_url = "http://api.airvisual.com/v2/nearest_city"
    params = {
        'lat': latitude,
        'lon': longitude,
        'key': api_key
    }
    
    full_url = f"{api_url}?{urlencode(params)}"
    print(f"Request URL: {api_url}?lat={latitude}&lon={longitude}&key={api_key[:8]}...")
    print()
    
    try:
        # Create request with proper headers
        request = Request(full_url)
        request.add_header('User-Agent', 'WeeWX-AirVisual-Test/1.0')
        request.add_header('Accept', 'application/json')
        
        print("Making API request...")
        
        # Make HTTP request with timeout
        with urlopen(request, timeout=30) as response:
            print(f"HTTP Status: {response.status}")
            
            if response.status != 200:
                print(f"❌ Error: API returned HTTP {response.status}")
                return False
            
            # Read and parse JSON response
            response_data = response.read().decode('utf-8')
            data = json.loads(response_data)
        
        print("✅ API request successful!")
        print()
        
        # Display full response (formatted)
        print("FULL API RESPONSE:")
        print("-" * 30)
        print(json.dumps(data, indent=2))
        print()
        
        # Parse and validate response
        print("PARSED DATA:")
        print("-" * 30)
        
        # Check response status
        if data.get('status') != 'success':
            print(f"❌ API Error: {data.get('status')}")
            return False
        
        # Navigate to pollution data
        current_data = data.get('data', {})
        if not current_data:
            print("❌ Missing 'data' section in response")
            return False
        
        # Location info
        city = current_data.get('city', 'Unknown')
        state = current_data.get('state', 'Unknown')
        country = current_data.get('country', 'Unknown')
        print(f"Location: {city}, {state}, {country}")
        
        pollution_data = current_data.get('current', {}).get('pollution', {})
        if not pollution_data:
            print("❌ Missing pollution data in response")
            return False
        
        # Extract key fields (US standard)
        aqius = pollution_data.get('aqius')
        mainus = pollution_data.get('mainus')
        timestamp = pollution_data.get('ts')
        
        print(f"Data Timestamp: {timestamp}")
        print(f"AQI (US): {aqius}")
        print(f"Main Pollutant (US): {mainus}")
        
        # Validate AQI value
        if aqius is None:
            print("❌ Missing 'aqius' field")
            return False
        
        if not isinstance(aqius, (int, float)) or aqius < 0:
            print(f"❌ Invalid AQI value: {aqius}")
            return False
        
        # Validate pollutant code
        valid_pollutants = ['p2', 'p1', 'o3', 'n2', 's2', 'co']
        if mainus not in valid_pollutants:
            print(f"⚠️ Warning: Unknown pollutant code: {mainus}")
        
        # Convert to WeeWX format
        print()
        print("WEEWX DATA FORMAT:")
        print("-" * 30)
        print(f"aqi: {int(aqius)}")
        print(f"main_pollutant: {convert_pollutant_code(mainus)}")
        print(f"aqi_level: {convert_aqi_to_level(aqius)}")
        
        print()
        print("✅ API test completed successfully!")
        print("Your API key and coordinates are working correctly.")
        
        return True
        
    except HTTPError as e:
        print(f"❌ HTTP Error: {e.code}")
        if e.code == 401:
            print("   → Invalid API key")
        elif e.code == 429:
            print("   → Rate limit exceeded")
        elif 500 <= e.code < 600:
            print("   → Server error")
        return False
        
    except URLError as e:
        print(f"❌ Network Error: {e.reason}")
        return False
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def convert_aqi_to_level(aqi):
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


def convert_pollutant_code(code):
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


def main():
    """Main function to run API test."""
    if len(sys.argv) != 4:
        print("Usage: python3 api_test.py API_KEY LATITUDE LONGITUDE")
        print()
        print("Example:")
        print("  python3 api_test.py abc123def456 33.656915 -117.982542")
        print()
        print("Get your free API key at: https://dashboard.iqair.com/")
        sys.exit(1)
    
    api_key = sys.argv[1]
    try:
        latitude = float(sys.argv[2])
        longitude = float(sys.argv[3])
    except ValueError:
        print("❌ Error: Latitude and longitude must be valid numbers")
        sys.exit(1)
    
    # Validate coordinates
    if not -90 <= latitude <= 90:
        print("❌ Error: Latitude must be between -90 and 90")
        sys.exit(1)
    
    if not -180 <= longitude <= 180:
        print("❌ Error: Longitude must be between -180 and 180")
        sys.exit(1)
    
    # Run the test
    success = test_api_connection(api_key, latitude, longitude)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
