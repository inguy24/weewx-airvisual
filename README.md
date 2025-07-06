# WeeWX AirVisual Extension

A WeeWX service extension that integrates IQ Air's AirVisual API to collect air quality data.

## Features

- ✅ Reads station coordinates from existing WeeWX configuration
- ✅ Exponential backoff retry logic with indefinite retries
- ✅ Thread-safe background data collection
- ✅ Proper WeeWX 5.1 extension integration
- ✅ Robust database schema management

## Quick Installation

```bash
weectl extension install weewx-airvisual.zip
```

## Requirements

- WeeWX 5.1+
- Python 3.7+
- IQ Air API key (free at https://dashboard.iqair.com/)

## Testing

See `tests/` directory for comprehensive test suite.

## Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Reference](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)

## License

GPL v3 - See LICENSE file for details.
