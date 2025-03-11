import socket
import threading
import json
import time
import datetime
import os
from flask import Flask, render_template, jsonify
import webbrowser
from threading import Thread


class ChatServer:
    def __init__(self, host="0.0.0.0", port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {client_socket: username}
        self.logs = []
        self.lock = threading.Lock()
        self.log_file_path = None

        # Create logs directory if it doesn't exist
        self.logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            print(f"Created logs directory: {self.logs_dir}")

        # Set up log file with timestamp in filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.logs_dir, f"chat_log_{timestamp}.txt")

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)

            self.log_event(
                "SERVER", "Server started on {}:{}".format(self.host, self.port)
            )
            self.log_event("SERVER", f"Logs being saved to: {self.log_file_path}")

            # Accept client connections in a separate thread
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()

            return True
        except Exception as e:
            print(f"Server error: {e}")
            return False

    def accept_connections(self):
        while True:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                self.log_event("SERVER", f"Error accepting connection: {e}")
                break

    def handle_client(self, client_socket, address):
        username = None

        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break

                message = json.loads(data.decode("utf-8"))

                if message["type"] == "connect":
                    username = message["username"]
                    with self.lock:
                        self.clients[client_socket] = username

                    self.log_event(
                        "CONNECT",
                        f"{username} connected from {address[0]}:{address[1]}",
                    )
                    self.broadcast_system_message(f"{username} has joined the chat")

                elif message["type"] == "disconnect":
                    break

                elif message["type"] == "message":
                    content = message["content"]
                    self.log_event("MESSAGE", f"{username}: {content}")
                    self.broadcast_message(username, content)

        except Exception as e:
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
                    username = self.clients[client_socket]
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
            print(f"[{timestamp}] [{event_type}] {message}")

        # Write to log file
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"[{timestamp}] [{event_type}] {message}\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")

    def shutdown(self):
        self.log_event("SERVER", "Server shutting down")

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


# Flask web interface
app = Flask(__name__)
chat_server = ChatServer()


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
        return jsonify(
            {
                "client_count": len(chat_server.clients),
                "clients": list(chat_server.clients.values()),
                "logs": chat_server.logs,
            }
        )


def start_web_server():
    app.run(host="0.0.0.0", port=8080, debug=False)


def main():
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
