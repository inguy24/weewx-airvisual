#!/usr/bin/env python3

"""
Simple functionality test for AirVisual utility functions
Tests the core functions without WeeWX dependencies
"""

import sys
import os

# Add the airvisual module path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bin', 'user'))

def test_utility_functions():
    """Test the utility functions from airvisual.py"""
    
    print("Testing AirVisual utility functions...")
    print("=" * 40)
    
    # Test AQI to level conversion
    print("\n1. Testing convert_aqi_to_level function:")
    
    # Read and execute just the function definitions
    with open('bin/user/airvisual.py', 'r') as f:
        content = f.read()
    
    # Extract the utility functions
    exec_globals = {}
    exec(content, exec_globals)
    
    convert_aqi_to_level = exec_globals['convert_aqi_to_level']
    convert_pollutant_code = exec_globals['convert_pollutant_code']
    
    # Test AQI conversion
    test_cases = [
        (25, "Good"),
        (52, "Moderate"),  # Your actual API result
        (125, "Unhealthy for Sensitive Groups"),
        (175, "Unhealthy"),
        (250, "Very Unhealthy"),
        (350, "Hazardous")
    ]
    
    all_passed = True
    for aqi, expected in test_cases:
        result = convert_aqi_to_level(aqi)
        status = "✅" if result == expected else "❌"
        print(f"   {status} AQI {aqi} → {result} (expected: {expected})")
        if result != expected:
            all_passed = False
    
    # Test pollutant conversion
    print("\n2. Testing convert_pollutant_code function:")
    pollutant_cases = [
        ('p2', 'PM2.5'),  # Your actual API result
        ('p1', 'PM10'),
        ('o3', 'Ozone'),
        ('n2', 'NO2'),
        ('s2', 'SO2'),
        ('co', 'CO')
    ]
    
    for code, expected in pollutant_cases:
        result = convert_pollutant_code(code)
        status = "✅" if result == expected else "❌"
        print(f"   {status} Code '{code}' → {result} (expected: {expected})")
        if result != expected:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✅ All utility function tests PASSED!")
        return True
    else:
        print("❌ Some tests FAILED!")
        return False

if __name__ == '__main__':
    success = test_utility_functions()
    sys.exit(0 if success else 1)
