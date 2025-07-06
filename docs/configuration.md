# Configuration Reference

## Service Configuration

The AirVisual service is configured in the `[AirVisualService]` section of `weewx.conf`:

```ini
[AirVisualService]
    enable = true
    api_key = YOUR_API_KEY_HERE
    interval = 600
    timeout = 30
    log_success = false
    log_errors = true
    retry_wait_base = 600
    retry_wait_max = 21600
    retry_multiplier = 2.0
```

## Configuration Options

### Basic Settings

- **enable**: Enable/disable the service (default: true)
- **api_key**: Your IQ Air API key (required)
- **interval**: Data collection interval in seconds (default: 600)
- **timeout**: HTTP request timeout in seconds (default: 30)

### Logging Settings

- **log_success**: Log successful API calls (default: false)
- **log_errors**: Log API errors and failures (default: true)

### Retry Settings

- **retry_wait_base**: Initial retry wait time in seconds (default: 600)
- **retry_wait_max**: Maximum retry wait time in seconds (default: 21600)
- **retry_multiplier**: Exponential backoff multiplier (default: 2.0)

## Station Coordinates

The service reads coordinates from the existing `[Station]` section:

```ini
[Station]
    latitude = 33.656915
    longitude = -117.982542
```

No need to duplicate coordinates in the AirVisual configuration.

## Rate Limits

- Free API: 10,000 calls/month
- Recommended interval: 10+ minutes
- Default interval (600s) uses ~4,300 calls/month
