import socket
import re
import threading
import json
import os
import subprocess
import tkinter as tk
from tkinter import messagebox
import obsws_python as obs

CONFIG_FILE = "config.json"

class TwitchOBSController:
    def __init__(self, root):
        self.root = root
        self.root.title("Twitch OBS Remote")
        self.root.geometry("400x380")
        
        self.config = self.load_config()
        self.running = False
        self.obs_client = None
        self.sock = None
        self.obs_connected = False

        # --- MENU BAR ---
        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Config", command=self.open_config_file)
        file_menu.add_command(label="Reload Config", command=self.reload_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)

        # --- UI ELEMENTS ---
        tk.Label(root, text="Twitch OBS Controller", font=("Arial", 16, "bold")).pack(pady=10)

        status_frame = tk.LabelFrame(root, text="Connection Status", padx=10, pady=10)
        status_frame.pack(padx=20, pady=10, fill="x")

        self.obs_label = tk.Label(status_frame, text="OBS: Disconnected", fg="red")
        self.obs_label.pack(anchor="w")

        self.twitch_label = tk.Label(status_frame, text="Twitch: Disconnected", fg="red")
        self.twitch_label.pack(anchor="w")

        self.user_frame = tk.LabelFrame(root, text="Allowed Users", padx=10, pady=10)
        self.user_frame.pack(padx=20, pady=10, fill="x")
        self.user_list_label = tk.Label(self.user_frame, text="", wraplength=300)
        self.user_list_label.pack()
        self.update_user_display()

        self.btn_toggle = tk.Button(root, text="START TOOL", bg="green", fg="white", 
                                   font=("Arial", 12, "bold"), command=self.toggle_tool)
        self.btn_toggle.pack(pady=20)

        self.monitor_connections()

    def load_config(self):
        placeholder = {
            "TWITCH_CHANNEL": "YOUR_CHANNEL_HERE",
            "ALLOWED_USERS": ["USER1", "USER2"],
            "OBS_HOST": "localhost",
            "OBS_PORT": 4455,
            "OBS_PW": "PASSWORD_HERE"
        }
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                json.dump(placeholder, f, indent=4)
            return placeholder
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    def is_config_valid(self):
        invalid_triggers = ["YOUR_CHANNEL_HERE", "PASSWORD_HERE", ""]
        channel = self.config.get("TWITCH_CHANNEL", "")
        password = self.config.get("OBS_PW", "")
        return channel not in invalid_triggers and password not in invalid_triggers

    def open_config_file(self):
        if os.name == 'nt':
            os.startfile(CONFIG_FILE)
        else:
            subprocess.call(('open', CONFIG_FILE))

    def reload_config(self):
        if self.running:
            messagebox.showwarning("Warning", "Stop the tool before reloading.")
            return
        self.config = self.load_config()
        self.update_user_display()
        messagebox.showinfo("Success", "Config reloaded.")

    def update_user_display(self):
        users = self.config.get('ALLOWED_USERS', [])
        self.user_list_label.config(text=", ".join(users) if users else "None")

    def update_status(self, label, text, color):
        label.config(text=text, fg=color)

    def monitor_connections(self):
        if self.running:
            # Twitch Check
            twitch_alive = False
            if self.sock:
                try:
                    if self.sock.fileno() != -1: twitch_alive = True
                except: pass
            
            if twitch_alive:
                chan = self.config.get('TWITCH_CHANNEL', '').lstrip('#')
                self.update_status(self.twitch_label, f"Twitch: #{chan} ✅", "green")
            else:
                self.update_status(self.twitch_label, "Twitch: Connection Lost ❌", "red")

            # OBS Check
            if self.obs_connected:
                try:
                    self.obs_client.get_version()
                    self.update_status(self.obs_label, "OBS: Connected ✅", "green")
                except:
                    self.obs_connected = False
                    self.update_status(self.obs_label, "OBS: Connection Lost (Searching...) ❌", "orange")
            else:
                threading.Thread(target=self.attempt_obs_connection, daemon=True).start()

        self.root.after(3000, self.monitor_connections)

    def attempt_obs_connection(self):
        try:
            self.obs_client = obs.ReqClient(
                host=self.config['OBS_HOST'], 
                port=self.config['OBS_PORT'], 
                password=self.config['OBS_PW'],
                timeout=3
            )
            self.obs_connected = True
        except Exception:
            self.obs_connected = False

    def toggle_tool(self):
        if not self.running:
            if not self.is_config_valid():
                messagebox.showerror("Config Error", "Please edit config.json and replace placeholder values.")
                return

            self.running = True
            self.btn_toggle.config(text="STOP TOOL", bg="red")
            self.update_status(self.obs_label, "OBS: Searching...", "orange")
            threading.Thread(target=self.run_twitch_backend, daemon=True).start()
        else:
            self.running = False
            self.btn_toggle.config(text="START TOOL", bg="green")
            self.cleanup()

    def cleanup(self):
        self.obs_connected = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except: pass
            self.sock = None
        
        self.obs_client = None
        
        self.root.after(0, lambda: self.update_status(self.obs_label, "OBS: Disconnected", "red"))
        self.root.after(0, lambda: self.update_status(self.twitch_label, "Twitch: Disconnected", "red"))

    def run_twitch_backend(self):
        try:
            raw_channel = self.config.get('TWITCH_CHANNEL', '').lstrip('#')
            clean_channel = f"#{raw_channel}"

            self.sock = socket.socket()
            self.sock.settimeout(1.0)
            self.sock.connect(("irc.chat.twitch.tv", 6667))
            self.sock.send(f"PASS anonymous\r\n".encode('utf-8'))
            self.sock.send(f"NICK justinfan12345\r\n".encode('utf-8'))
            self.sock.send(f"JOIN {clean_channel}\r\n".encode('utf-8'))

            buffer = ""
            while self.running:
                try:
                    data = self.sock.recv(2048).decode('utf-8', errors='ignore')
                    if not data: break
                    buffer += data
                    lines = buffer.split("\r\n")
                    buffer = lines.pop()

                    for line in lines:
                        if line.startswith('PING'):
                            self.sock.send("PONG\r\n".encode('utf-8'))
                            continue
                        
                        match = re.search(r':(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)', line)
                        if match:
                            user, msg = match.group(1).lower(), match.group(2).strip().lower()
                            
                            # Check if user is allowed
                            if user in [u.lower() for u in self.config.get('ALLOWED_USERS', [])]:
                                if self.obs_connected:
                                    try:
                                        if msg.startswith("!start"):
                                            self.obs_client.start_stream()
                                        elif msg.startswith("!stop"):
                                            self.obs_client.stop_stream()
                                    except Exception as e:
                                        print(f"OBS Command Error: {e}")
                except socket.timeout: continue 
                except OSError: break 
        except Exception as e:
            if self.running: 
                self.root.after(0, lambda: messagebox.showerror("Twitch Error", f"Twitch failed: {e}"))
        
        self.cleanup()
        self.running = False
        self.root.after(0, lambda: self.btn_toggle.config(text="START TOOL", bg="green"))

if __name__ == "__main__":
    root = tk.Tk()
    app = TwitchOBSController(root)
    root.mainloop()