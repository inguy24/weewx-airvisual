# Changelog

## [1.0.0] - 2025-01-XX

### Added
- Initial release of WeeWX AirVisual extension
- IQ Air API integration for air quality data
- Exponential backoff retry logic with indefinite retries
- Thread-safe background data collection
- Robust database schema management
- WeeWX 5.1 extension architecture compliance
- Interactive installation with API key setup
- Configuration reading from existing [Station] section
- Unit system integration for AQI data
- Comprehensive error handling and logging

### Features
- Collects AQI, main pollutant, and air quality level data
- Respects API rate limits (10,000 calls/month)
- Non-blocking operation with WeeWX main loop
- Automatic database field creation and management
- Graceful handling of API outages and network issues
