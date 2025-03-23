import socket
import threading
import json
import time
import datetime
import os
import signal
import sys
from flask import Flask, render_template, jsonify, request, Response, send_from_directory
import webbrowser
from threading import Thread
import logging


class ChatServer:
    def __init__(self, host="0.0.0.0", port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {client_socket: {"username": username, "last_active": timestamp}}
        self.logs = []
        self.lock = threading.Lock()
        self.log_file_path = None
        self.active = True
        self.message_history = []  # Store recent messages for new clients
        self.max_history = 50  # Max number of messages to store

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('ChatServer')

        # Create logs directory if it doesn't exist
        self.logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            self.logger.info(f"Created logs directory: {self.logs_dir}")

        # Set up log file with timestamp in filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.logs_dir, f"chat_log_{timestamp}.txt")

        # Set up file handler for logging
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(file_handler)

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)  # Increased from 5 to 10

            self.log_event(
                "SERVER", f"Server started on {self.host}:{self.port}"
            )
            self.log_event("SERVER", f"Logs being saved to: {self.log_file_path}")

            # Start heartbeat mechanism to detect disconnected clients
            heartbeat_thread = threading.Thread(target=self.client_heartbeat)
            heartbeat_thread.daemon = True
            heartbeat_thread.start()

            # Accept client connections in a separate thread
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()

            return True
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            return False

    def accept_connections(self):
        while self.active:
            try:
                self.server_socket.settimeout(1.0)  # Set timeout for accept() to allow checking self.active
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client, args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue  # Timeout allows checking self.active condition
            except Exception as e:
                if self.active:  # Only log if not shutting down
                    self.log_event("SERVER", f"Error accepting connection: {e}")
                break

    def handle_client(self, client_socket, address):
        username = None

        try:
            # Set a timeout for initial connection
            client_socket.settimeout(10.0)

            # Wait for initial connect message
            data = client_socket.recv(4096)
            if not data:
                return

            message = json.loads(data.decode("utf-8"))

            if message["type"] == "connect":
                username = message["username"]

                # Reset timeout for normal operation
                client_socket.settimeout(None)

                with self.lock:
                    self.clients[client_socket] = {
                        "username": username,
                        "address": f"{address[0]}:{address[1]}",
                        "last_active": time.time(),
                        "connected_at": time.time()
                    }

                self.log_event(
                    "CONNECT",
                    f"{username} connected from {address[0]}:{address[1]}",
                )
                self.broadcast_system_message(f"{username} has joined the chat")

                # Send recent message history to the new client
                self.send_history(client_socket)

                # Main message processing loop
                while self.active:
                    data = client_socket.recv(4096)
                    if not data:
                        break

                    # Update last active timestamp
                    with self.lock:
                        if client_socket in self.clients:
                            self.clients[client_socket]["last_active"] = time.time()

                    message = json.loads(data.decode("utf-8"))

                    if message["type"] == "disconnect":
                        break
                    elif message["type"] == "message":
                        content = message["content"]
                        self.log_event("MESSAGE", f"{username}: {content}")

                        # Store in message history
                        with self.lock:
                            self.message_history.append({
                                "type": "message",
                                "username": username,
                                "content": content,
                                "timestamp": time.time()
                            })
                            # Trim history if needed
                            if len(self.message_history) > self.max_history:
                                self.message_history = self.message_history[-self.max_history:]

                        self.broadcast_message(username, content)
                    elif message["type"] == "ping":
                        # Respond to ping with a pong
                        try:
                            client_socket.send(json.dumps({"type": "pong"}).encode("utf-8"))
                        except:
                            break

        except json.JSONDecodeError:
            self.log_event("ERROR", f"Invalid JSON from client {address}")
        except Exception as e:
            if self.active:  # Only log if not shutting down
                self.log_event(
                    "ERROR",
                    f"Error handling client {username if username else 'unknown'}: {e}",
                )

        finally:
            # Clean up on disconnect
            if username:
                with self.lock:
                    if client_socket in self.clients:
                        del self.clients[client_socket]

                self.log_event("DISCONNECT", f"{username} disconnected")
                self.broadcast_system_message(f"{username} has left the chat")

            try:
                client_socket.close()
            except:
                pass

    def send_history(self, client_socket):
        """Send recent message history to a newly connected client"""
        try:
            with self.lock:
                # Send the last N messages from history
                for msg in self.message_history[-20:]:  # Send last 20 messages
                    client_socket.send(json.dumps(msg).encode("utf-8"))

            # Send a welcome message
            client_socket.send(
                json.dumps({
                    "type": "system",
                    "content": "Welcome to the chat! Here are the most recent messages.",
                    "timestamp": time.time()
                }).encode("utf-8")
            )
        except Exception as e:
            self.logger.error(f"Error sending history: {e}")

    def client_heartbeat(self):
        """Periodically check for inactive clients and clean them up"""
        while self.active:
            time.sleep(30)  # Check every 30 seconds

            current_time = time.time()
            inactive_timeout = 120  # 2 minutes

            disconnected_clients = []

            with self.lock:
                for client_socket, info in list(self.clients.items()):
                    if current_time - info["last_active"] > inactive_timeout:
                        try:
                            # Try to send a ping
                            client_socket.send(json.dumps({"type": "ping"}).encode("utf-8"))
                        except:
                            # Failed to send - client is disconnected
                            disconnected_clients.append((client_socket, info["username"]))

            # Clean up disconnected clients
            for client_socket, username in disconnected_clients:
                with self.lock:
                    if client_socket in self.clients:
                        del self.clients[client_socket]

                self.log_event("DISCONNECT", f"{username} disconnected (timeout)")
                self.broadcast_system_message(f"{username} has left the chat (timeout)")

                try:
                    client_socket.close()
                except:
                    pass

    def broadcast_message(self, sender, content):
        message = json.dumps(
            {
                "type": "message",
                "username": sender,
                "content": content,
                "timestamp": time.time(),
            }
        )

        self.broadcast(message)

    def broadcast_system_message(self, content):
        message = json.dumps(
            {"type": "system", "content": content, "timestamp": time.time()}
        )

        self.broadcast(message)

    def broadcast(self, message_json):
        disconnected_clients = []

        with self.lock:
            for client_socket in self.clients:
                try:
                    client_socket.send(message_json.encode("utf-8"))
                except:
                    disconnected_clients.append(client_socket)

        # Clean up any disconnected clients
        for client_socket in disconnected_clients:
            with self.lock:
                if client_socket in self.clients:
                    username = self.clients[client_socket]["username"]
                    del self.clients[client_socket]
                    self.log_event(
                        "DISCONNECT", f"{username} disconnected (connection error)"
                    )

    def log_event(self, event_type, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {"timestamp": timestamp, "type": event_type, "message": message}

        # Add to in-memory logs
        with self.lock:
            self.logs.append(log_entry)

        # Log to console and file via logger
        if event_type == "ERROR":
            self.logger.error(f"[{event_type}] {message}")
        else:
            self.logger.info(f"[{event_type}] {message}")

        # Write to log file directly for redundancy
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] [{event_type}] {message}\n")
        except Exception as e:
            self.logger.error(f"Error writing to log file: {e}")

    def shutdown(self):
        self.active = False
        self.log_event("SERVER", "Server shutting down")

        # Notify all clients
        try:
            self.broadcast_system_message("Server is shutting down...")
        except:
            pass

        # Give clients a moment to receive the shutdown message
        time.sleep(1)

        # Disconnect all clients
        with self.lock:
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.close()
                except:
                    pass

            self.clients.clear()

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


# Flask web interface with enhanced features
app = Flask(__name__)
chat_server = ChatServer()

# Create templates directory if it doesn't exist
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)

    # Create a basic dashboard.html template
    with open(os.path.join(templates_dir, "dashboard.html"), "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Whisper Chat - Server Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background-color: #2b2b2b;
            color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #3c3f41;
        }
        h1, h2, h3 {
            color: #4f99e3;
        }
        .status-card, .clients-card, .logs-card {
            background-color: #3c3f41;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-box {
            background-color: #4f99e3;
            color: white;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            text-align: left;
            padding: 8px 12px;
            border-bottom: 1px solid #444;
        }
        th {
            background-color: #333;
            color: #4f99e3;
        }
        tr:hover {
            background-color: #383838;
        }
        .log-entry {
            margin-bottom: 5px;
            padding: 8px;
            border-left: 3px solid #4f99e3;
            background-color: #333;
        }
        .log-timestamp {
            color: #a7a7a7;
            font-size: 12px;
        }
        .log-type {
            font-weight: bold;
            margin-right: 10px;
        }
        .type-CONNECT { color: #4CAF50; }
        .type-DISCONNECT { color: #FF5722; }
        .type-MESSAGE { color: #2196F3; }
        .type-SERVER { color: #9C27B0; }
        .type-ERROR { color: #F44336; }
        .refresh-button {
            background-color: #4f99e3;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        .refresh-button:hover {
            background-color: #3d78b3;
        }
        .auto-refresh {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .logs-container {
            max-height: 500px;
            overflow-y: auto;
            background-color: #333;
            border-radius: 4px;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Whisper Chat Server Dashboard</h1>
            <div>
                <button onclick="refreshData()" class="refresh-button">Refresh Data</button>
            </div>
        </header>

        <div class="stats">
            <div class="stat-box">
                <div class="stat-value" id="clientCount">0</div>
                <div class="stat-label">Active Clients</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="messageCount">0</div>
                <div class="stat-label">Messages</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="serverUptime">00:00:00</div>
                <div class="stat-label">Uptime</div>
            </div>
        </div>

        <div class="status-card">
            <h2>Server Status</h2>
            <p>Server Host: <strong>{{ host }}</strong></p>
            <p>Server Port: <strong>{{ port }}</strong></p>
            <p>Log File: <strong>{{ log_file }}</strong></p>
            <p>Status: <strong id="serverStatus">Running</strong></p>
        </div>

        <div class="clients-card">
            <h2>Connected Clients</h2>
            <table id="clientsTable">
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>IP Address</th>
                        <th>Connected Since</th>
                        <th>Last Active</th>
                    </tr>
                </thead>
                <tbody id="clientsList">
                    <tr>
                        <td colspan="4">Loading clients...</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="logs-card">
            <h2>Server Logs</h2>
            <div class="auto-refresh">
                <input type="checkbox" id="autoRefresh" checked>
                <label for="autoRefresh">Auto-refresh (5s)</label>
            </div>
            <div class="logs-container">
                <div id="logsList">Loading logs...</div>
            </div>
        </div>
    </div>

    <script>
        let startTime = new Date();
        let messageCounter = 0;
        let autoRefreshInterval;

        // Initial data load
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            setupAutoRefresh();
        });

        function setupAutoRefresh() {
            const autoRefreshCheckbox = document.getElementById('autoRefresh');

            function toggleAutoRefresh() {
                if (autoRefreshCheckbox.checked) {
                    autoRefreshInterval = setInterval(refreshData, 5000);
                } else {
                    clearInterval(autoRefreshInterval);
                }
            }

            autoRefreshCheckbox.addEventListener('change', toggleAutoRefresh);
            toggleAutoRefresh(); // Initial setup
        }

        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    updateClientsList(data.clients_detailed);
                    updateLogsList(data.logs);

                    // Update stats
                    document.getElementById('clientCount').textContent = data.client_count;
                    messageCounter = data.message_count;
                    document.getElementById('messageCount').textContent = messageCounter;

                    // Update uptime
                    updateUptime();
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        }

        function updateClientsList(clients) {
            const clientsList = document.getElementById('clientsList');

            if (!clients || clients.length === 0) {
                clientsList.innerHTML = '<tr><td colspan="4">No clients connected</td></tr>';
                return;
            }

            let html = '';

            clients.forEach(client => {
                const connectedSince = new Date(client.connected_at * 1000);
                const lastActive = new Date(client.last_active * 1000);

                html += `<tr>
                    <td>${escapeHtml(client.username)}</td>
                    <td>${escapeHtml(client.address)}</td>
                    <td>${formatDate(connectedSince)}</td>
                    <td>${formatDate(lastActive)}</td>
                </tr>`;
            });

            clientsList.innerHTML = html;
        }

        function updateLogsList(logs) {
            const logsList = document.getElementById('logsList');

            if (!logs || logs.length === 0) {
                logsList.innerHTML = '<div class="log-entry">No logs available</div>';
                return;
            }

            let html = '';

            logs.slice().reverse().forEach(log => {
                html += `<div class="log-entry">
                    <span class="log-timestamp">${log.timestamp}</span>
                    <span class="log-type type-${log.type}">[${log.type}]</span>
                    <span class="log-message">${escapeHtml(log.message)}</span>
                </div>`;

                // Count messages for stats
                if (log.type === 'MESSAGE') {
                    messageCounter++;
                }
            });

            logsList.innerHTML = html;
        }

        function updateUptime() {
            const now = new Date();
            const diff = now - startTime;

            // Convert to hours, minutes, seconds
            const hours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);

            const formattedUptime = 
                String(hours).padStart(2, '0') + ':' + 
                String(minutes).padStart(2, '0') + ':' + 
                String(seconds).padStart(2, '0');

            document.getElementById('serverUptime').textContent = formattedUptime;
        }

        function formatDate(date) {
            return date.toLocaleString();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
""")

# Create static directory if needed
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)


@app.route("/")
def index():
    return render_template(
        "dashboard.html",
        host=chat_server.host,
        port=chat_server.port,
        log_file=chat_server.log_file_path,
    )


@app.route("/api/status")
def status():
    with chat_server.lock:
        # Get more detailed client info
        clients_detailed = [
            {
                "username": info["username"],
                "address": info["address"],
                "connected_at": info["connected_at"],
                "last_active": info["last_active"]
            }
            for info in chat_server.clients.values()
        ]

        return jsonify(
            {
                "client_count": len(chat_server.clients),
                "clients": list(info["username"] for info in chat_server.clients.values()),
                "clients_detailed": clients_detailed,
                "logs": chat_server.logs,
                "message_count": sum(1 for log in chat_server.logs if log["type"] == "MESSAGE")
            }
        )


@app.route("/api/logs")
def download_logs():
    """Endpoint to download the current log file"""
    if not os.path.exists(chat_server.log_file_path):
        return "Log file not found", 404

    return send_from_directory(
        os.path.dirname(chat_server.log_file_path),
        os.path.basename(chat_server.log_file_path),
        as_attachment=True
    )


@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(static_dir, path)


def start_web_server():
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)


def signal_handler(sig, frame):
    print("\nShutting down server...")
    chat_server.shutdown()
    sys.exit(0)


def main():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start chat server
    if not chat_server.start():
        print("Failed to start chat server. Exiting.")
        return

    # Start web interface in a separate thread
    web_thread = Thread(target=start_web_server)
    web_thread.daemon = True
    web_thread.start()

    # Open web browser
    webbrowser.open("http://localhost:8080")

    print("Whisper Chat server is running. Press Ctrl+C to stop.")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        chat_server.shutdown()


if __name__ == "__main__":
    main()