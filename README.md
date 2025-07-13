# WeeWX AirVisual Extension

A robust WeeWX extension that integrates IQ Air's AirVisual API to collect air quality data and seamlessly inject it into your WeeWX weather station database.

## 🌟 Features

- **Real-time Air Quality Data**: Collects AQI (Air Quality Index), main pollutant, and air quality level
- **Seamless WeeWX Integration**: Data appears alongside your weather data in reports and graphs
- **Bulletproof Reliability**: Exponential backoff retry logic with indefinite retries - never gives up!
- **Smart Configuration**: Uses your existing station coordinates, no duplication needed
- **Robust Error Handling**: Handles API outages, rate limits, and network issues gracefully
- **Easy Installation**: Automated installer with interactive setup
- **Production Ready**: Thread-safe operation with clean shutdown handling

## 📊 Data Collected

The extension adds three fields to your WeeWX database:

| Field | Description | Example Values |
|-------|-------------|----------------|
| `aqi` | Air Quality Index (0-500+) | 42, 125, 301 |
| `main_pollutant` | Primary pollutant | PM2.5, Ozone, NO2 |
| `aqi_level` | Descriptive air quality level | Good, Moderate, Unhealthy |

## ⚠️ Alpha Release - User Testing Needed!

**This is an Alpha release that needs user testing and feedback.** Please help us improve by:
- Testing the installation and configuration process
- Reporting any issues or bugs you encounter
- Sharing feedback about the user experience
- Contributing to discussions about features and improvements

## 🚀 Installation

### Prerequisites
- WeeWX 5.1 or later
- Python 3.7 or later
- Internet connection for API access

### Step 1: Get Your Free API Key

1. Visit [IQ Air Dashboard](https://dashboard.iqair.com/)
2. Create a free account
3. Click "Air quality API" in the left menu
4. Click "+ Create an API key"
5. Select "Community" plan (free, 10,000 calls/month)
6. Save your API key - you'll need it during installation

### Step 2: Install the Extension

```bash
# Install directly from GitHub release
weectl extension install https://github.com/inguy24/weewx-airvisual/releases/download/v1.0.0a/weewx-airvisual-v1.0.0a.zip

# The installer will prompt you for:
# - Your IQ Air API key
# - Data collection interval (default: 10 minutes)

# Restart WeeWX to activate the extension
sudo systemctl restart weewx
```

### Step 3: Verify Installation

Check your WeeWX logs to confirm successful startup:

```bash
sudo journalctl -u weewx -f
```

Look for these messages:
- ✅ "AirVisual service version 1.0.0 starting"
- ✅ "AirVisual service initialized successfully"
- ✅ "Collected air quality data: AQI=42, pollutant=PM2.5, level=Good"

### Step 4: Help Us Test!

After installation, please:
1. **Monitor the logs** for any errors or warnings
2. **Check that data appears** in your WeeWX database and reports
3. **Report issues** at [GitHub Issues](https://github.com/inguy24/weewx-airvisual/issues)
4. **Share your experience** in [GitHub Discussions](https://github.com/inguy24/weewx-airvisual/discussions)

## 🚀 Quick Start (Summary)

**For detailed installation instructions, see the [Installation](#-installation) section above.**

The basic process is:
1. Get free API key from [IQ Air Dashboard](https://dashboard.iqair.com/)
2. Install: `weectl extension install https://github.com/inguy24/weewx-airvisual/releases/download/v1.0.0a/weewx-airvisual-v1.0.0a.zip`
3. Follow prompts for API key and interval
4. Restart WeeWX: `sudo systemctl restart weewx`
5. Check logs and help us test!

## ⚙️ Configuration

The installer automatically configures the extension, but you can customize settings in `weewx.conf`:

```ini
[AirVisualService]
    enable = true
    api_key = YOUR_API_KEY_HERE
    interval = 600                    # Data collection interval (seconds)
    timeout = 30                      # HTTP request timeout
    log_success = false               # Log successful API calls
    log_errors = true                 # Log errors and failures
    
    # Exponential backoff retry configuration
    retry_wait_base = 600             # Start with 10 minutes
    retry_wait_max = 21600            # Max 6 hours between retries
    retry_multiplier = 2.0            # Double wait time each failure
```

**Note**: The extension automatically reads your station coordinates from the existing `[Station]` section - no need to duplicate them!

## 📈 API Usage & Rate Limits

- **Free Community Plan**: 10,000 calls/month
- **Default Interval**: 10 minutes (600 seconds)
- **Monthly Usage**: ~4,300 calls (well within limits)
- **Rate Limit Safety**: Built-in rate limiting prevents quota exceeded errors

To adjust your data collection frequency:

```ini
[AirVisualService]
    interval = 900    # 15 minutes (more conservative)
    interval = 300    # 5 minutes (more frequent, uses quota faster)
```

## 🔧 Architecture & Reliability

### Exponential Backoff Retry Logic

When API calls fail, the extension doesn't give up. Instead, it uses smart retry logic:

- **Normal Operation**: Collect data every 10 minutes
- **On Failure**: Wait 10min → 20min → 40min → 80min → max 6 hours
- **Recovery**: Automatically returns to normal interval when API comes back online
- **Never Stops**: Keeps trying indefinitely - no manual intervention needed

### Thread-Safe Design

- **Background Operation**: API calls don't block WeeWX operations
- **Thread-Safe Data**: Proper locking ensures data integrity
- **Clean Shutdown**: Graceful termination when WeeWX stops

### Error Handling

The extension handles all common failure scenarios:

- **Rate Limit Exceeded**: Automatic backoff and retry
- **Network Outages**: Exponential backoff retry
- **Invalid API Key**: Clear error message with solution
- **API Maintenance**: Transparent retry until service restored

## 🗃️ Database Integration

### Automatic Schema Extension

The installer automatically adds the required database fields:

```sql
ALTER TABLE archive ADD COLUMN aqi REAL;
ALTER TABLE archive ADD COLUMN main_pollutant VARCHAR(10);
ALTER TABLE archive ADD COLUMN aqi_level VARCHAR(30);
```

### Data Integrity

- **Data Validation**: Checks AQI ranges and pollutant codes
- **Freshness Check**: Only injects recent data (within 2 intervals)
- **Safe Defaults**: Uses NULL for missing/stale data
- **Unit System**: Properly integrates with WeeWX unit system

## 📋 Troubleshooting

### Common Issues

**"api_key is required but not provided"**
- Run `weectl extension install airvisual.zip` to reconfigure
- Check API key in `[AirVisualService]` section of `weewx.conf`

**"API authentication failed - check API key"**
- Verify API key is correct at [IQ Air Dashboard](https://dashboard.iqair.com/)
- Test with: `python3 examples/api_test.py YOUR_API_KEY LAT LON`

**"API rate limit exceeded"**
- Increase interval in configuration (e.g., `interval = 900`)
- Check if other applications are using the same API key

**"no such column: aqi"**
- Database fields weren't created during installation
- Manually add fields:
  ```bash
  weectl database add-column aqi --type REAL
  weectl database add-column main_pollutant --type VARCHAR(10)
  weectl database add-column aqi_level --type VARCHAR(30)
  ```

### Debug Mode

Enable detailed logging in `weewx.conf`:

```ini
[AirVisualService]
    log_success = true
    log_errors = true

[Logging]
    [[loggers]]
        [[[user.airvisual]]]
            level = DEBUG
```

### Test Your Setup

The extension includes a test script to verify your API key and coordinates:

```bash
cd /path/to/extension/examples
python3 api_test.py YOUR_API_KEY 33.656915 -117.982542
```

## 📖 Usage Examples

### Reporting and Visualization

Once installed, air quality data appears in your WeeWX reports alongside weather data. You can create custom reports using the new fields:

```html
<!-- In your skin templates -->
<p>Current Air Quality: $current.aqi AQI ($current.aqi_level)</p>
<p>Main Pollutant: $current.main_pollutant</p>

<!-- Historical data -->
<p>Yesterday's Average AQI: $yesterday.aqi.avg</p>
<p>This Week's Maximum AQI: $week.aqi.max</p>
```

### Database Queries

Access air quality data directly from the database:

```sql
-- Recent air quality readings
SELECT datetime(dateTime, 'unixepoch', 'localtime') as date, 
       aqi, main_pollutant, aqi_level 
FROM archive 
WHERE aqi IS NOT NULL 
ORDER BY dateTime DESC 
LIMIT 10;

-- Daily air quality averages
SELECT date(datetime(dateTime, 'unixepoch', 'localtime')) as date,
       ROUND(AVG(aqi), 1) as avg_aqi,
       MAX(aqi) as max_aqi
FROM archive 
WHERE aqi IS NOT NULL 
GROUP BY date 
ORDER BY date DESC;
```

## 🔄 Upgrade and Maintenance

### Updating the Extension

```bash
# Download new version when available
weectl extension install https://github.com/inguy24/weewx-airvisual/releases/download/v1.0.0a/weewx-airvisual-v1.0.0a.zip

# Reinstall (preserves configuration)
# Follow prompts if configuration changes are needed

# Restart WeeWX
sudo systemctl restart weewx
```

### API Key Renewal

The Community API key is valid for 12 months after which it will expire. You must then go back to the AirVisual website, delete your old key, create a new one following the same steps and update your configuration with the new key.

1. Visit [IQ Air Dashboard](https://dashboard.iqair.com/)
2. Delete your old expired key
3. Create a new key
4. Update `weewx.conf` with new key
5. Restart WeeWX

## 🗑️ Uninstallation

```bash
# Remove the extension
weectl extension uninstall AirVisual

# Restart WeeWX
sudo systemctl restart weewx
```

**Note**: This removes the service but preserves your air quality data in the database.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/inguy24/weewx-airvisual.git
cd weewx-airvisual

# Run tests
python3 tests/test_airvisual.py

# Test API integration
python3 examples/api_test.py YOUR_API_KEY LAT LON
```

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [IQ Air](https://www.iqair.com/) for providing the AirVisual API
- [WeeWX](https://weewx.com/) team for the excellent weather station software
- WeeWX community for extension development guidance

## 📞 Support

- **Issues & Bug Reports**: [GitHub Issues](https://github.com/inguy24/weewx-airvisual/issues)
- **Questions & Discussions**: [GitHub Discussions](https://github.com/inguy24/weewx-airvisual/discussions)
- **WeeWX User Group**: [Google Groups](https://groups.google.com/g/weewx-user)

### Alpha Testing Feedback

Since this is an Alpha release, we especially need feedback on:
- **Installation Process**: Did the installer work smoothly?
- **Configuration**: Were the prompts clear and helpful?
- **Data Collection**: Is air quality data appearing correctly?
- **Error Handling**: How well does it handle network issues or API problems?
- **Performance**: Any impact on WeeWX performance?
- **Documentation**: Is anything unclear or missing?

Please share your experience in [GitHub Discussions](https://github.com/inguy24/weewx-airvisual/discussions) or report bugs in [GitHub Issues](https://github.com/inguy24/weewx-airvisual/issues).

---

**Built with ❤️ for cleaner air awareness and better health monitoring.**