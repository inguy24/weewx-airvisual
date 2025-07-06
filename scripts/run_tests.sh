#!/bin/bash

# WeeWX AirVisual Extension Test Runner
set -e

echo "WeeWX AirVisual Extension - Test Runner"
echo "======================================"

# Check if we're in the right directory
if [ ! -f "bin/user/airvisual.py" ]; then
    echo "❌ Error: airvisual.py not found. Are you in the repository root?"
    exit 1
fi

# Run unit tests
echo "Running unit tests..."
if command -v pytest &> /dev/null; then
    echo "Using pytest..."
    python3 -m pytest tests/test_airvisual.py -v
else
    echo "Using unittest..."
    python3 tests/test_airvisual.py
fi

# Run API test if API key provided
if [ $# -eq 3 ]; then
    echo
    echo "Running API integration test..."
    python3 examples/api_test.py "$1" "$2" "$3"
else
    echo
    echo "To run API integration test:"
    echo "  ./scripts/run_tests.sh YOUR_API_KEY LATITUDE LONGITUDE"
    echo "  Example: ./scripts/run_tests.sh abc123 33.656915 -117.982542"
fi

echo
echo "✅ Test execution complete"
