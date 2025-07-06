# Troubleshooting Guide

## Common Issues

### API Key Problems

**Error: "api_key is required but not provided"**
- Solution: Run `weectl extension install` again to reconfigure
- Verify API key in weewx.conf `[AirVisualService]` section

**Error: "API authentication failed - check API key"**
- Verify API key is correct
- Check API key hasn't expired
- Test with examples/api_test.py script

### Rate Limiting

**Error: "API rate limit exceeded"**
- Increase interval in configuration
- Check other applications using same API key
- Monitor usage at https://dashboard.iqair.com/

### Network Issues

**Error: "Network error connecting to API"**
- Check internet connectivity
- Verify firewall allows outbound HTTP on port 80
- Try different DNS servers

### Database Issues

**Error: "no such column: aqi"**
- Database fields not created during installation
- Run manual field addition:
  ```bash
  weectl database add-column aqi --type REAL
  weectl database add-column main_pollutant --type VARCHAR(10)
  weectl database add-column aqi_level --type VARCHAR(30)
  ```

### Service Not Starting

**Check WeeWX logs:**
```bash
sudo journalctl -u weewx -f
```

**Common causes:**
- Invalid coordinates in [Station] section
- Missing Python dependencies
- Permission errors

## Debug Mode

Enable debug logging in weewx.conf:

```ini
[AirVisualService]
    log_success = true
    log_errors = true

[Logging]
    [[loggers]]
        [[[user.airvisual]]]
            level = DEBUG
```

## Getting Help

1. Check WeeWX logs first
2. Test API key with examples/api_test.py
3. Run unit tests: python3 tests/test_airvisual.py
4. Post to WeeWX user group with logs
