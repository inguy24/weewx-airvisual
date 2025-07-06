# Installation Guide

## Prerequisites

- WeeWX 5.1 or later
- Python 3.7 or later
- IQ Air API key (free registration)

## Step 1: Get API Key

1. Visit https://dashboard.iqair.com/
2. Create free account (Community plan)
3. Create API key
4. Note your API key for installation

## Step 2: Install Extension

```bash
# Download the extension package
wget https://github.com/YOUR_USERNAME/weewx-airvisual/releases/latest/download/weewx-airvisual.zip

# Install using weectl
weectl extension install weewx-airvisual.zip

# Follow prompts to enter API key and interval
```

## Step 3: Restart WeeWX

```bash
sudo systemctl restart weewx
```

## Step 4: Verify Installation

Check WeeWX logs for successful startup:

```bash
sudo journalctl -u weewx -f
```

Look for messages like:
- "AirVisual service version 1.0.0 starting"
- "AirVisual service initialized successfully"

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for common issues.
