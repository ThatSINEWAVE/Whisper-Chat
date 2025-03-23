import socket
import threading
import json
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
from datetime import datetime
import os


class ModernChatClient:
    def __init__(self, host="localhost", port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None
        self.connected = False
        self.message_history = []

        # Create logs directory for saving chat history
        self.logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

        # Set up the main window
        self.root = tk.Tk()
        self.root.title("Whisper Chat")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)

        # Set theme colors
        self.colors = {
            "bg_dark": "#2b2b2b",
            "bg_light": "#3c3f41",
            "accent": "#4f99e3",
            "text": "#f0f0f0",
            "text_muted": "#a7a7a7",
            "sent_msg": "#3b7ebd",
            "received_msg": "#404040",
            "system_msg": "#5c6bc0"
        }

        # Configure styles
        self.root.configure(bg=self.colors["bg_dark"])
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure('TFrame', background=self.colors["bg_dark"])
        self.style.configure('TButton',
                             background=self.colors["accent"],
                             foreground=self.colors["text"],
                             borderwidth=0,
                             focusthickness=0,
                             font=('Segoe UI', 10))
        self.style.map('TButton',
                       background=[('active', self.colors["accent"])])

        self.create_login_ui()

    def create_login_ui(self):
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create a frame for login
        login_frame = ttk.Frame(self.root, style='TFrame')
        login_frame.pack(expand=True)

        # App title
        title_label = tk.Label(login_frame,
                               text="Whisper Chat",
                               font=('Segoe UI', 24, 'bold'),
                               bg=self.colors["bg_dark"],
                               fg=self.colors["accent"])
        title_label.pack(pady=(0, 20))

        # Subtitle
        subtitle_label = tk.Label(login_frame,
                                  text="Connect and chat securely",
                                  font=('Segoe UI', 12),
                                  bg=self.colors["bg_dark"],
                                  fg=self.colors["text_muted"])
        subtitle_label.pack(pady=(0, 30))

        # Username frame
        username_frame = ttk.Frame(login_frame)
        username_frame.pack(pady=10)

        username_label = tk.Label(username_frame,
                                  text="Username",
                                  font=('Segoe UI', 10),
                                  bg=self.colors["bg_dark"],
                                  fg=self.colors["text"])
        username_label.pack(anchor="w", padx=5)

        self.username_entry = tk.Entry(username_frame,
                                       font=('Segoe UI', 12),
                                       bg=self.colors["bg_light"],
                                       fg=self.colors["text"],
                                       insertbackground=self.colors["text"],
                                       relief=tk.FLAT,
                                       width=25)
        self.username_entry.pack(pady=5, ipady=5, padx=5)

        # Server settings frame
        server_frame = ttk.Frame(login_frame)
        server_frame.pack(pady=10)

        server_label = tk.Label(server_frame,
                                text="Server",
                                font=('Segoe UI', 10),
                                bg=self.colors["bg_dark"],
                                fg=self.colors["text"])
        server_label.pack(anchor="w", padx=5)

        self.server_entry = tk.Entry(server_frame,
                                     font=('Segoe UI', 12),
                                     bg=self.colors["bg_light"],
                                     fg=self.colors["text"],
                                     insertbackground=self.colors["text"],
                                     relief=tk.FLAT,
                                     width=25)
        self.server_entry.insert(0, self.host)
        self.server_entry.pack(pady=5, ipady=5, padx=5)

        # Port frame
        port_frame = ttk.Frame(login_frame)
        port_frame.pack(pady=10)

        port_label = tk.Label(port_frame,
                              text="Port",
                              font=('Segoe UI', 10),
                              bg=self.colors["bg_dark"],
                              fg=self.colors["text"])
        port_label.pack(anchor="w", padx=5)

        self.port_entry = tk.Entry(port_frame,
                                   font=('Segoe UI', 12),
                                   bg=self.colors["bg_light"],
                                   fg=self.colors["text"],
                                   insertbackground=self.colors["text"],
                                   relief=tk.FLAT,
                                   width=25)
        self.port_entry.insert(0, str(self.port))
        self.port_entry.pack(pady=5, ipady=5, padx=5)

        # Connect button
        self.connect_button = ttk.Button(login_frame,
                                         text="Connect",
                                         command=self.attempt_connection,
                                         style='TButton',
                                         width=15)
        self.connect_button.pack(pady=20)

        # Status label
        self.status_label = tk.Label(login_frame,
                                     text="",
                                     font=('Segoe UI', 10),
                                     bg=self.colors["bg_dark"],
                                     fg=self.colors["text_muted"])
        self.status_label.pack(pady=5)

        # Set focus to username entry
        self.username_entry.focus()

        # Bind Enter key to connect
        self.root.bind('<Return>', lambda event: self.attempt_connection())

    def create_chat_ui(self):
        # Clear any existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()

        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = tk.Label(header_frame,
                               text=f"Whisper Chat",
                               font=('Segoe UI', 14, 'bold'),
                               bg=self.colors["bg_dark"],
                               fg=self.colors["accent"])
        title_label.pack(side=tk.LEFT)

        self.connection_label = tk.Label(header_frame,
                                         text=f"Connected as: {self.username}",
                                         font=('Segoe UI', 10),
                                         bg=self.colors["bg_dark"],
                                         fg=self.colors["text_muted"])
        self.connection_label.pack(side=tk.RIGHT)

        # Chat area frame (messages display)
        self.chat_frame = ttk.Frame(main_container)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)

        # Create and configure the message display area
        self.message_area = scrolledtext.ScrolledText(
            self.chat_frame,
            bg=self.colors["bg_light"],
            fg=self.colors["text"],
            font=('Segoe UI', 10),
            padx=10,
            pady=10,
            wrap=tk.WORD,
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.message_area.pack(fill=tk.BOTH, expand=True)

        # Input area
        input_frame = ttk.Frame(main_container)
        input_frame.pack(fill=tk.X, pady=(10, 0))

        self.message_entry = tk.Text(
            input_frame,
            bg=self.colors["bg_light"],
            fg=self.colors["text"],
            font=('Segoe UI', 10),
            height=3,
            padx=10,
            pady=10,
            wrap=tk.WORD,
            relief=tk.FLAT,
            insertbackground=self.colors["text"]
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.message_entry.focus()

        # Send button
        self.send_button = ttk.Button(
            input_frame,
            text="Send",
            command=self.send_message_ui,
            width=10
        )
        self.send_button.pack(side=tk.RIGHT, padx=(10, 0))

        # Status bar
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill=tk.X, pady=(5, 0))

        self.status_text = tk.StringVar()
        self.status_text.set("Connected to server")

        status_label = tk.Label(
            status_frame,
            textvariable=self.status_text,
            font=('Segoe UI', 8),
            bg=self.colors["bg_dark"],
            fg=self.colors["text_muted"],
            anchor=tk.W
        )
        status_label.pack(side=tk.LEFT, fill=tk.X)

        # Disconnect button
        self.disconnect_button = ttk.Button(
            status_frame,
            text="Disconnect",
            command=self.disconnect,
            width=10
        )
        self.disconnect_button.pack(side=tk.RIGHT)

        # Bind Enter key to send message
        self.message_entry.bind('<Return>', self.handle_return)

        # Show welcome message
        self.display_system_message(f"Welcome to Whisper Chat, {self.username}!")
        self.display_system_message(f"Connected to {self.host}:{self.port}")

    def handle_return(self, event):
        # Don't add newline when Enter is pressed
        if not event.state & 0x1:  # If Shift is not pressed
            self.send_message_ui()
            return "break"  # Prevents the default newline behavior

    def attempt_connection(self):
        self.username = self.username_entry.get().strip()
        self.host = self.server_entry.get().strip()

        try:
            self.port = int(self.port_entry.get().strip())
        except ValueError:
            self.status_label.config(text="Invalid port number")
            return

        if not self.username:
            self.status_label.config(text="Please enter a username")
            return

        self.status_label.config(text="Connecting...")

        # Run connection in a thread to prevent freezing the UI
        connection_thread = threading.Thread(target=self.connect)
        connection_thread.daemon = True
        connection_thread.start()

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            # Send username to server
            self.socket.send(
                json.dumps({"type": "connect", "username": self.username}).encode("utf-8")
            )

            # Start thread to receive messages
            self.connected = True
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()

            # Update UI
            self.root.after(0, self.create_chat_ui)

            # Create a chat log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file_path = os.path.join(self.logs_dir, f"chat_log_{timestamp}.txt")
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"=== Chat session started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                log_file.write(f"Connected to {self.host}:{self.port} as {self.username}\n\n")

        except Exception as e:
            error_message = f"Connection error: {e}"
            print(error_message)
            self.root.after(0, lambda: self.status_label.config(text=error_message))

    def send_message_ui(self):
        # Get message from the text widget
        message = self.message_entry.get("1.0", tk.END).strip()

        if message:
            # Clear the message entry
            self.message_entry.delete("1.0", tk.END)

            # Display the message
            self.display_sent_message(self.username, message)

            # Send the message
            self.send_message(message)

            # Save to history
            self.save_to_log(self.username, message)

    def send_message(self, message):
        if not message or not self.connected:
            return

        try:
            self.socket.send(
                json.dumps(
                    {"type": "message", "username": self.username, "content": message}
                ).encode("utf-8")
            )
        except Exception as e:
            self.display_system_message(f"Error sending message: {e}")

    def receive_messages(self):
        while self.connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.root.after(0, lambda: self.display_system_message("Disconnected from server"))
                    self.connected = False
                    break

                message = json.loads(data.decode("utf-8"))

                if message["type"] == "message":
                    # Don't display our own messages (already displayed when sent)
                    if message["username"] != self.username:
                        self.root.after(0, lambda msg=message: self.display_received_message(
                            msg["username"], msg["content"]
                        ))
                        self.save_to_log(message["username"], message["content"])

                elif message["type"] == "system":
                    self.root.after(0, lambda msg=message: self.display_system_message(
                        msg["content"]
                    ))
                    self.save_to_log("SYSTEM", message["content"])

            except Exception as e:
                self.root.after(0, lambda e=e: self.display_system_message(f"Error receiving message: {e}"))
                self.connected = False
                break

        # Try to reconnect or show reconnect button
        self.root.after(0, lambda: self.status_text.set("Disconnected from server"))

    def display_sent_message(self, username, content):
        self.message_area.config(state=tk.NORMAL)

        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M")

        # Insert message with username in bold and message bubble styling
        self.message_area.insert(tk.END, f"\n{timestamp} ", "timestamp")
        self.message_area.insert(tk.END, f"{username}: ", "sent_user")
        self.message_area.insert(tk.END, f"{content}\n", "sent_msg")

        # Apply tags for styling
        self.message_area.tag_config("timestamp", foreground=self.colors["text_muted"], font=('Segoe UI', 8))
        self.message_area.tag_config("sent_user", foreground=self.colors["accent"], font=('Segoe UI', 10, 'bold'))
        self.message_area.tag_config("sent_msg", foreground=self.colors["text"])

        # Scroll to bottom
        self.message_area.see(tk.END)
        self.message_area.config(state=tk.DISABLED)

    def display_received_message(self, username, content):
        self.message_area.config(state=tk.NORMAL)

        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M")

        # Insert message with username in bold
        self.message_area.insert(tk.END, f"\n{timestamp} ", "timestamp")
        self.message_area.insert(tk.END, f"{username}: ", "recv_user")
        self.message_area.insert(tk.END, f"{content}\n", "recv_msg")

        # Apply tags for styling
        self.message_area.tag_config("timestamp", foreground=self.colors["text_muted"], font=('Segoe UI', 8))
        self.message_area.tag_config("recv_user", foreground="#9ccc65", font=('Segoe UI', 10, 'bold'))
        self.message_area.tag_config("recv_msg", foreground=self.colors["text"])

        # Scroll to bottom
        self.message_area.see(tk.END)
        self.message_area.config(state=tk.DISABLED)

    def display_system_message(self, content):
        self.message_area.config(state=tk.NORMAL)

        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M")

        # Insert system message
        self.message_area.insert(tk.END, f"\n{timestamp} ", "timestamp")
        self.message_area.insert(tk.END, f"System: {content}\n", "system_msg")

        # Apply tags for styling
        self.message_area.tag_config("timestamp", foreground=self.colors["text_muted"], font=('Segoe UI', 8))
        self.message_area.tag_config("system_msg", foreground=self.colors["accent"], font=('Segoe UI', 10, 'italic'))

        # Scroll to bottom
        self.message_area.see(tk.END)
        self.message_area.config(state=tk.DISABLED)

    def save_to_log(self, username, message):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] {username}: {message}\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")

    def disconnect(self):
        if self.connected and self.socket:
            try:
                self.socket.send(
                    json.dumps({"type": "disconnect", "username": self.username}).encode("utf-8")
                )
                self.socket.close()
            except:
                pass

        self.connected = False
        self.socket = None

        # Return to login screen
        self.create_login_ui()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        if self.connected:
            if messagebox.askokcancel("Quit", "Are you sure you want to disconnect and quit?"):
                self.disconnect()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    client = ModernChatClient()
    client.run()


if __name__ == "__main__":
    main()