import socket
import re
import threading
import json
import os
import zlib
import base64
import time
import webbrowser
import requests
import customtkinter as ctk
import obsws_python as obs
from packaging import version
from typing import Dict, Any

VERSION = "2.1.4"
CONFIG_FILE = "settings.dat"

# ==========================================
# 1. Configuration Manager
# ==========================================
class ConfigManager:
    """Handles loading and saving the encrypted settings.dat file."""
    @staticmethod
    def load() -> Dict[str, Any]:
        placeholder = {
            "TWITCH_CHANNEL": "YOUR_CHANNEL_HERE", 
            "ALLOWED_USERS": ["USER1"], 
            "OBS_HOST": "localhost", 
            "OBS_PORT": 4455, 
            "OBS_PW": "PASSWORD_HERE", 
            "window_x": None, 
            "window_y": None
        }
        if not os.path.exists(CONFIG_FILE):
            ConfigManager.save(placeholder)
            return placeholder
        try:
            with open(CONFIG_FILE, "rb") as f:
                return json.loads(zlib.decompress(base64.b64decode(f.read())).decode('utf-8'))
        except Exception:
            return placeholder

    @staticmethod
    def save(data: Dict[str, Any]):
        json_str = json.dumps(data)
        compressed = zlib.compress(json_str.encode('utf-8'))
        with open(CONFIG_FILE, "wb") as f:
            f.write(base64.b64encode(compressed))


# ==========================================
# 2. OBS WebSocket Manager
# ==========================================
class OBSManager:
    """Handles all communication with OBS Studio."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.is_connected = False

    def connect(self) -> bool:
        try:
            self.client = obs.ReqClient(
                host=self.config.get('OBS_HOST', 'localhost'), 
                port=self.config.get('OBS_PORT', 4455), 
                password=self.config.get('OBS_PW', ''), 
                timeout=3
            )
            self.client.get_version() # Heartbeat check
            self.is_connected = True
            return True
        except Exception:
            self.disconnect()
            return False

    def disconnect(self):
        self.is_connected = False
        self.client = None

    def get_stream_status(self) -> bool:
        if not self.is_connected or not self.client: return False
        try:
            return self.client.get_stream_status().output_active
        except Exception:
            self.disconnect()
            return False
    
    def get_scene_list(self):
        if not self.is_connected or not self.client: 
            return None
        try:
            return self.client.get_scene_list()
        except Exception as e:
            return None

    def execute_command(self, cmd: str, args: str = ""):
        if not self.is_connected or not self.client: return
        try:
            if cmd == "start":
                self.client.start_stream()
            elif cmd == "stop":
                self.client.stop_stream()
            elif cmd == "scene" and args:
                self.client.set_current_program_scene(args)
        except Exception as e:
            print(f"OBS Command Error: {e}")


# ==========================================
# 3. Twitch IRC Bot
# ==========================================
class TwitchBot:
    """Runs the Twitch IRC connection in a background thread."""
    def __init__(self, config: Dict[str, Any], obs_manager: OBSManager):
        self.config = config
        self.obs_manager = obs_manager
        self.sock = None
        self.running = False
        self.is_connected = False

    def start(self):
        self.running = True
        threading.Thread(target=self._run_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.is_connected = False
        if self.sock:
            try: self.sock.close()
            except: pass
            self.sock = None

    def _run_loop(self):
        reconnect_delay = 1
        while self.running:
            try:
                chan = f"#{self.config.get('TWITCH_CHANNEL', '').lstrip('#')}"
                self.sock = socket.socket()
                self.sock.settimeout(1.0)
                self.sock.connect(("irc.chat.twitch.tv", 6667))
                self.sock.send(f"PASS anonymous\r\nNICK justinfan123\r\nJOIN {chan}\r\n".encode('utf-8'))
                
                self.is_connected = True
                reconnect_delay = 1  
                
                self.buffer = ""
                while self.running:
                    try:
                        new_data = self.sock.recv(2048).decode('utf-8', errors='ignore')
                        if not new_data: break # Connection closed

                        self.buffer += new_data
                        while "\r\n" in self.buffer:
                            line, self.buffer = self.buffer.split("\r\n", 1)
                            line = line.strip()

                            if not line: continue

                            if line.startswith("PING"):
                                self.sock.send(f"PONG {line.split()[1]}\r\n".encode('utf-8'))
                                continue

                            self._process_message(line)
                    except socket.timeout:
                        continue
                    except Exception:
                        break # Socket error, break to reconnect
            except Exception:
                self.is_connected = False
                if self.running:
                    reconnect_delay = min(reconnect_delay * 2, 30)
                    time.sleep(reconnect_delay)
        self.stop()

    def _process_message(self, data: str):
        match = re.search(r':(\w+)!.*PRIVMSG #\w+ :(.+)', data)
        if not match: return
        
        user, msg = match.group(1).lower(), match.group(2).strip()
        allowed_users = [u.lower() for u in self.config.get('ALLOWED_USERS', [])]
        
        if user in allowed_users:
            cmd = msg.lower()
            if cmd.startswith("!start"):
                self.obs_manager.execute_command("start")
            elif cmd.startswith("!stop"):
                self.obs_manager.execute_command("stop")
            elif cmd.startswith("!scene "):
                raw_name = msg[7:].strip()
                scene_name = "".join(char for char in raw_name if char.isprintable()).strip()  # Remove non-printable characters
                scene_name = scene_name.encode("ascii", "ignore").decode("ascii").strip()  # Remove non-ASCII characters (important because spamprotector can inject weird unicode chars)

                scene_list_response = self.obs_manager.get_scene_list()
                scene_list = [s['sceneName'] for s in scene_list_response.scenes]

                found_match = None
                # prioritize case-sensitive exact match
                if scene_name in scene_list:
                    found_match = scene_name
                else:
                    # otherwise take first case-insensitive match
                    for scene in scene_list:
                        if scene.lower() == scene_name.lower():
                            found_match = scene
                            break
                if found_match:
                    self.obs_manager.execute_command("scene", found_match)


# ==========================================
# 4. User Interface (Main App)
# ==========================================
class TwitchOBSApp:
    """Handles the CustomTkinter GUI and orchestrates the backend managers."""
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("IRL OBS Commander")
        
        self.config = ConfigManager.load()
        self.obs = OBSManager(self.config)
        self.twitch = TwitchBot(self.config, self.obs)
        
        self.setup_window()
        self.build_ui()
        self.show_waiting_status()
        
        self.alert_timer_id = None
        self.obs_reconnect_thread = None

    def setup_window(self):
        width, height = 460, 500
        pos_x, pos_y = self.config.get("window_x"), self.config.get("window_y")
        if pos_x is not None and pos_y is not None:
            self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        else:
            self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def build_ui(self):
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.main = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.main.pack(fill="both", expand=True, padx=20, pady=(10, 5))

        # Nav Bar
        self.nav_bar = ctk.CTkFrame(self.main, height=40, fg_color="transparent")
        self.nav_bar.pack(fill="x", pady=(0, 10))
        self.file_menu = ctk.CTkOptionMenu(self.nav_bar, values=["Settings", "Check for updates", "Exit"], command=self.handle_menu, width=110, dynamic_resizing=False)
        self.file_menu.set("Menu")
        self.file_menu.pack(side="left")

        # Header & Alerts
        self.alert_label = ctk.CTkLabel(self.main, text="", font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        self.alert_label.pack(side="bottom", fill="x", pady=(5, 0))
        ctk.CTkLabel(self.main, text="IRL OBS Commander", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(10, 20))

        # Status Card
        self.status_card = ctk.CTkFrame(self.main)
        self.status_card.pack(fill="x", pady=5)
        ctk.CTkLabel(self.status_card, text="SYSTEM STATUS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#747D8C").pack(anchor="w", padx=15, pady=(10, 5))
        
        self.waiting_label = ctk.CTkLabel(self.status_card, text="Waiting for commander to start...", font=ctk.CTkFont(size=14, slant="italic"), text_color="#95a5a6")
        self.obs_label = ctk.CTkLabel(self.status_card, text="OBS: Reconnecting", font=ctk.CTkFont(size=14))
        self.twitch_label = ctk.CTkLabel(self.status_card, text="Twitch: Disconnected", font=ctk.CTkFont(size=14))
        self.stream_label = ctk.CTkLabel(self.status_card, text="Stream: Offline", font=ctk.CTkFont(size=14))

        # User Card
        self.user_card = ctk.CTkFrame(self.main)
        self.user_card.pack(fill="x", pady=15)
        ctk.CTkLabel(self.user_card, text="PERMITTED USERS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#747D8C").pack(anchor="w", padx=15, pady=(10, 5))
        self.user_list_label = ctk.CTkLabel(self.user_card, text=", ".join(self.config.get('ALLOWED_USERS', [])) or "None", wraplength=380, font=ctk.CTkFont(size=13))
        self.user_list_label.pack(padx=20, pady=(0, 15))

        # Start Button
        self.btn_toggle = ctk.CTkButton(self.main, text="START COMMANDER", fg_color="#27ae60", hover_color="#2ecc71", font=ctk.CTkFont(size=15, weight="bold"), height=45, command=self.toggle_system)
        self.btn_toggle.pack(fill="x", pady=(10, 0))

    # --- UI Status Management ---
    def show_waiting_status(self):
        self.obs_label.pack_forget()
        self.twitch_label.pack_forget()
        self.stream_label.pack_forget()
        self.waiting_label.pack(pady=(5, 15))

    def show_active_status(self):
        self.waiting_label.pack_forget()
        self.obs_label.pack(anchor="w", padx=20)
        self.twitch_label.pack(anchor="w", padx=20)
        self.stream_label.pack(anchor="w", padx=20, pady=(0, 15))

    def update_label(self, label, text, color):
        colors = {"green": "#2ecc71", "red": "#e74c3c", "orange": "#f39c12", "gray": "#95a5a6"}
        label.configure(text=text, text_color=colors.get(color, color))

    def show_alert(self, text, color="#e74c3c", duration_in_ms=5000):
        if self.alert_timer_id: self.root.after_cancel(self.alert_timer_id)
        self.alert_label.configure(text=text, text_color=color)
        self.alert_timer_id = self.root.after(duration_in_ms, lambda: self.alert_label.configure(text=""))

    # --- Main System Loop ---
    def toggle_system(self):
        if not self.twitch.running:
            if any(x in [self.config.get("TWITCH_CHANNEL"), self.config.get("OBS_PW")] for x in ["YOUR_CHANNEL_HERE", "PASSWORD_HERE", ""]):
                self.show_alert("Please update settings first.")
                return
            
            self.btn_toggle.configure(text="STOP COMMANDER", fg_color="#c0392b", hover_color="#e74c3c")
            self.show_active_status()
            self.twitch.start()
            self.monitor_loop()
        else:
            self.twitch.stop()
            self.obs.disconnect()
            self.btn_toggle.configure(text="START COMMANDER", fg_color="#27ae60", hover_color="#2ecc71")
            self.show_waiting_status()

    def monitor_loop(self):
        if not self.twitch.running: return

        # Update Twitch UI
        if self.twitch.is_connected:
            chan = self.config.get('TWITCH_CHANNEL', '').lstrip('#')
            self.update_label(self.twitch_label, f"Twitch: #{chan} ✅", "green")
        else:
            self.update_label(self.twitch_label, "Twitch: Connection Lost ❌", "red")

        # Update OBS UI & Handle Reconnection
        if self.obs.is_connected and self.obs.client:
            try:
                self.obs.client.get_version() # Heartbeat
                self.update_label(self.obs_label, "OBS: Connected ✅", "green")
                
                if self.obs.get_stream_status():
                    self.update_label(self.stream_label, "Stream: LIVE 🔴", "red")
                else:
                    self.update_label(self.stream_label, "Stream: Offline", "gray")
            except Exception:
                self.obs.disconnect()
        else:
            self.update_label(self.obs_label, "OBS: Reconnecting...", "orange")
            self.update_label(self.stream_label, "Stream: Unknown", "gray")
            
            # Spin up a background thread to reconnect to OBS so the UI doesn't freeze
            if not self.obs_reconnect_thread or not self.obs_reconnect_thread.is_alive():
                self.obs_reconnect_thread = threading.Thread(target=self.obs.connect, daemon=True)
                self.obs_reconnect_thread.start()

        self.root.after(3000, self.monitor_loop)

    # --- Windows & Menus ---
    def handle_menu(self, choice):
        if choice == "Settings":
            if self.twitch.running:
                self.show_alert("Stop the commander before changing settings.")
            else:
                self.open_settings()
        elif choice == "Check for updates":
            self.check_for_updates()
        elif choice == "Exit":
            self.on_closing()
        self.file_menu.set("Menu")

    def open_settings(self):
        # Settings UI Logic
        win = ctk.CTkToplevel(self.root)
        win.title("Settings")
        win.geometry(f"400x450+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")
        win.transient(self.root)
        win.grab_set()

        fields = {}
        for label, key in [("Twitch Channel", "TWITCH_CHANNEL"), ("Allowed Users (comma-separated)", "ALLOWED_USERS"), 
                           ("OBS Host", "OBS_HOST"), ("OBS Port", "OBS_PORT"), ("OBS Password", "OBS_PW")]:
            ctk.CTkLabel(win, text=label, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20)
            entry = ctk.CTkEntry(win, width=360, show="*" if "Password" in label else "")
            val = self.config.get(key, "")
            entry.insert(0, ", ".join(val) if isinstance(val, list) else str(val))
            entry.pack(pady=(0, 15), padx=20)
            fields[key] = entry

        def save():
            try:
                self.config.update({
                    "TWITCH_CHANNEL": fields["TWITCH_CHANNEL"].get().strip(),
                    "ALLOWED_USERS": [u.strip() for u in fields["ALLOWED_USERS"].get().split(",") if u.strip()],
                    "OBS_HOST": fields["OBS_HOST"].get().strip(),
                    "OBS_PORT": int(fields["OBS_PORT"].get().strip()),
                    "OBS_PW": fields["OBS_PW"].get().strip()
                })
                ConfigManager.save(self.config)
                self.obs = OBSManager(self.config)      # Re-init managers with new config
                self.twitch = TwitchBot(self.config, self.obs)
                self.user_list_label.configure(text=", ".join(self.config.get('ALLOWED_USERS', [])) or "None")
                self.show_alert("Settings saved.", "#2ecc71")
                win.destroy()
            except Exception as e:
                self.show_alert(f"Save Error: {e}")

        version_info = ctk.CTkLabel(
            win, 
            text=f"IRL OBS Commander v{VERSION}", 
            font=ctk.CTkFont(size=10), 
            text_color="#747D8C",
            cursor="hand2"
        )
        version_info.pack(side="bottom", pady=10)
        version_info.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Lewster2307/IRL-OBS-Commander"))

        ctk.CTkButton(win, text="Save", command=save).pack(pady=10)

    def check_for_updates(self):
        try:
            url = "https://api.github.com/repos/Lewster2307/IRL-OBS-Commander/releases/latest"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                latest_tag = response.json().get("tag_name", "").replace("v", "")
                current_tag = VERSION.replace("v", "")
                
                if version.parse(latest_tag) > version.parse(current_tag):
                    self.show_alert(f"Update available: v{latest_tag} (Current: v{current_tag})", "#f39c12", duration_in_ms=15000)
                    webbrowser.open("https://github.com/Lewster2307/IRL-OBS-Commander/releases/latest")
                else:
                    self.show_alert(f"You are running the latest version (v{VERSION}).", "#2ecc71")
            else:
                self.show_alert("Failed to check for updates.", "#e74c3c")
        except Exception as e:
            self.show_alert(f"Update check failed: {e}", "#e74c3c")

    def on_closing(self):
        self.config["window_x"], self.config["window_y"] = self.root.winfo_x(), self.root.winfo_y()
        ConfigManager.save(self.config)
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = TwitchOBSApp(root)
    root.mainloop()