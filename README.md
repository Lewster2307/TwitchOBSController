# Twitch OBS Remote Controller

A Python application that allows Twitch chat users to remotely control OBS (Open Broadcaster Software) streaming via IRC chat commands.

## Features

- **Twitch Chat Integration**: Connects to Twitch IRC to monitor chat messages
- **OBS Control**: Start and stop streaming directly from Twitch chat
- **User Access Control**: Only specified users can execute commands
- **Connection Monitoring**: Real-time GUI status indicators for both Twitch and OBS connections
- **Configuration Management**: Easy-to-edit JSON config file
- **Minimal Console**: Runs with no visible console window via batch file

## Requirements

- Python 3.x
- Virtual environment (`.venv`)
- Tkinter (usually included with Python)

### Python Dependencies

```
obsws-python==1.8.0
websocket-client==1.9.0
```

## Installation & Setup

1. **Clone or download** this repository to your local machine

2. **Create a virtual environment** (if not already present):
   ```bash
   python -m venv .venv
   ```

3. **Install dependencies**:
   ```bash
   .\.venv\Scripts\pip.exe install -r .\requirements.txt
   ```

4. **Set up OBS WebSocket (requires OBS Studio version 28 or newer for built-in WebSocket support or install the [plugin](https://github.com/obsproject/obs-websocket/releases/tag/5.0.0) for older versions)**:
   - Tools > WebSockets Server Settings
   - Enable WebSockets server
   - Configure the server port (usually 4455) and password in OBS
   - Ensure the host and port match your `config.json` settings

5. **Configure the application**:
   - Edit `config.json` with your settings:
     ```json
        {
            "TWITCH_CHANNEL": "YOUR_CHANNEL_HERE",
            "ALLOWED_USERS": [
                "USER1",
                "USER2"
            ],
            "OBS_HOST": "localhost",
            "OBS_PORT": 4455,
            "OBS_PW": "PASSWORD_HERE"
        }
     ```

## Usage

### GUI Launch

**Run the application**:
```bash
python script.py
```

Or double-click `TwitchOBSController.bat` for a clean launch (no console window).

### GUI Interface

- **Connection Status**: Shows real-time connection status for OBS and Twitch
- **Allowed Users**: Displays which users can control the stream
- **START/STOP Buttons**: Toggle the monitoring tool on/off
- **Menu Options**:
  - **Open Config**: Opens `config.json` in your default editor
  - **Reload Config**: Reloads configuration without restarting
  - **Exit**: Closes the application

### Chat Commands

Once the tool is running, authorized users can control OBS via Twitch chat:

- **`!start`** - Start streaming in OBS
- **`!stop`** - Stop streaming in OBS

**Example**:
```
User: !start
Bot: [Stream starts in OBS]
```

## Troubleshooting

### OBS Connection Lost (Orange)
- Verify OBS is running and WebSocket plugin is active
- Check that `OBS_HOST` and `OBS_PORT` in config match your OBS settings
- Confirm OBS WebSocket password is correct

### Twitch Connection Lost (Red)
- Check internet connection
- Verify `TWITCH_CHANNEL` is correctly configured
- The tool will auto-reconnect every 3 seconds

### Config Not Accepting Changes
- Stop the tool before reloading config (use "Reload Config" from menu)
- Verify placeholder values are replaced with actual settings

### Commands Not Working
- Ensure the command-issuing user is in `ALLOWED_USERS`
- Confirm OBS is connected (status shows green)
- Commands are case-insensitive but must start with `!`

## Security Notes

⚠️ **Important**:
- Store `OBS_PW` securely - it provides direct control over OBS
- Only add trusted users to `ALLOWED_USERS`
- Do not share `config.json` publicly (contains sensitive credentials)
- Consider using environment variables for production deployments

## File Structure

```
TwitchOBSController/
├── script.py                    # Main application
├── config.json                  # Configuration file
├── requirements.txt             # Python dependencies
├── TwitchOBSController.bat      # Windows launcher (no console)
├── .venv/                       # Virtual environment (local)
├── .gitignore                   # Git ignore file
└── README.md                    # This file
```
