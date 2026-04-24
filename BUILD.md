# Build Instructions

1. **Create a virtual environment** (if not already present):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. **Install dependencies** (if not already installed):
   ```bash
   pip install -r .\requirements.txt
   ```

3. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```

4. **Build the executable (windows)**
   ```bash
   pyinstaller --onefile --noconsole --name "TwitchOBSController" script.py
   ```
    - `--onefile`: Creates a single executable file.
    - `--noconsole`: Hides the console window when running the application.
    - `--name`: Specifies the name of the output executable.

5. The generated executable will be located in the `dist` folder as `TwitchOBSController.exe`.
