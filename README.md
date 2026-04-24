# Twitch OBS Remote Controller

A Python application that allows Twitch chat users to remotely control OBS (Open Broadcaster Software) streaming via IRC chat commands.

## Features

- **Twitch Chat Integration**: Connects to Twitch IRC to monitor chat messages
- **OBS Control**: Start and stop streaming and change scenes directly from Twitch chat
- **User Access Control**: Only specified users can execute commands
- **Connection Monitoring**: Real-time GUI status indicators for both Twitch and OBS connections

## Installation & Setup

- Download the latest binary release from the [releases](https://github.com/Lewster2307/TwitchOBSController/releases) page
- **Set up OBS WebSocket (requires OBS Studio version 28 or newer for built-in WebSocket support or install the [plugin](https://github.com/obsproject/obs-websocket/releases/tag/5.0.0) for older versions)**:
   - Tools > WebSockets Server Settings
   - Enable WebSockets server
   - Configure the server port (usually 4455) and password in OBS
- Start the TwitchOBSController.exe to auto generate the `settings.dat` file
- Go to Menu > Settings to enter your Twitch channel name, allowed users, and OBS credentials.

> [!NOTE]  
> Because this is an unsigned standalone executable, Windows SmartScreen may show a warning. This is common for open-source tools. You can bypass this by clicking "More Info" > "Run Anyway". Alternatively, you can run the source code directly as explained in the [Setup for development](#setup-for-development) section or build your own executable as explained in the [BUILD.md](BUILD.md) file.

## Usage

### Interface

- **Waiting for controller to start:** App is idle and waiting for user to start the controller
- **OBS Status:**
  - **Connected:** Ready for commands.
  - **Reconnecting:** Attempting to find OBS (Check if OBS is open and websocket is enabled).**
- **Twitch Status:** Shows the currently monitored channel or connection loss.
- **Stream Status:** Displays a live indicator if the stream is currently broadcasting.

### Chat Commands

Once the tool is running, authorized users can control OBS via Twitch chat:

| Command         | Action              | Notes |
| :-------------- | :------------------ | :---- |
| `!start`        | **Start Streaming** | Triggers the "Start Streaming" command in OBS. |
| `!stop`         | **Stop Streaming**  | Triggers the "Stop Streaming" command in OBS. |
| `!scene <name>` | **Change Scene**    | Switches to the specified scene. Name must match OBS **exactly** (case-sensitive). |

**Example**:
```
User: !start -> OBS starts streaming
User: !scene IRL -> OBS switches to the "IRL" scene
```

## Troubleshooting

### OBS Connection Lost (Orange)

- Verify OBS is running and WebSocket plugin is active
- Check that `OBS Host` and `OBS Port` in config match your OBS settings
- Confirm OBS WebSocket password in `OBS Password` is correct

### Twitch Connection Lost (Red)

- Check internet connection
- Verify `Twitch Channel` is correctly configured
- The tool will auto-reconnect every 3 seconds

### Config Not Accepting Changes

- Stop the tool before reloading config (use "Reload Config" from menu)
- Verify placeholder values are replaced with actual settings

### Commands Not Working

- Ensure the command-issuing user is in `Allowed Users`
- Confirm OBS is connected (status shows green)
- Commands are case-insensitive but must start with `!`

## Security Notes

⚠️ **Important**:
- Store `OBS_PW` securely - it provides direct control over OBS
- Only add trusted users to `Allowed Users` to prevent unauthorized access




<br><br>
<a id="setup-for-development"></a>
<details>
<summary><strong>Click for the setup for development</strong></summary>

## Setup for development

### Requirements

- Python 3.x
- Virtual environment (`.venv`)

### Python Dependencies

```
customtkinter==5.2.2
darkdetect==0.8.0
obsws-python==1.8.0
packaging==26.1
websocket-client==1.9.0
```

### Installation & Setup

1. **Clone or download** this repository to your local machine

2. **Create a virtual environment** (if not already present):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r .\requirements.txt
   ```

4. **Set up OBS WebSocket (requires OBS Studio version 28 or newer for built-in WebSocket support or install the [plugin](https://github.com/obsproject/obs-websocket/releases/tag/5.0.0) for older versions)**:
   - Tools > WebSockets Server Settings
   - Enable WebSockets server
   - Configure the server port (usually 4455) and password in OBS

5. **Run the application**:
   ```bash
   python script.py
   ```

### Building the Executable

Instructions for building a standalone executable using PyInstaller can be found in the [BUILD.md](BUILD.md) file.

### File Structure

```
TwitchOBSController/
├── script.py                    # Main application
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore file
├── BUILD.md                     # Build instructions
├── README.md                    # This file
├── settings.dat                 # Configuration file (auto-generated on first run)
├────────────────────(local development)─────────────────────────────────
├── .venv/                       # Virtual environment
├── dist/                        # Build output
├── build/                       # Build artifacts
└── TwitchOBSController.spec     # PyInstaller spec file
```

</details>