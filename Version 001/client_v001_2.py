import socket
import threading
import json
import sys


class ChatClient:
    def __init__(self, host="localhost", port=9999):
        self.host = host
        self.port = port
        self.socket = None
        self.username = None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            # Send username to server
            self.socket.send(
                json.dumps({"type": "connect", "username": self.username}).encode(
                    "utf-8"
                )
            )

            # Start thread to receive messages
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()

            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def send_message(self, message):
        if not message:
            return

        try:
            self.socket.send(
                json.dumps(
                    {"type": "message", "username": self.username, "content": message}
                ).encode("utf-8")
            )
        except Exception as e:
            print(f"Error sending message: {e}")

    def receive_messages(self):
        while True:
            try:
                data = self.socket.recv(4096)
                if not data:
                    print("Disconnected from server")
                    break

                message = json.loads(data.decode("utf-8"))
                if message["type"] == "message":
                    print(f"{message['username']}: {message['content']}")
                elif message["type"] == "system":
                    print(f"[SYSTEM] {message['content']}")
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def disconnect(self):
        if self.socket:
            try:
                self.socket.send(
                    json.dumps(
                        {"type": "disconnect", "username": self.username}
                    ).encode("utf-8")
                )
                self.socket.close()
            except:
                pass


def main():
    client = ChatClient()

    # Get username
    client.username = input("Enter your username: ")

    # Connect to server
    print("Connecting to chat server...")
    if not client.connect():
        print("Failed to connect to server. Exiting.")
        sys.exit(1)

    print(f"Connected as {client.username}. Type 'exit' to quit.")

    # Main message loop
    try:
        while True:
            message = input()
            if message.lower() == "exit":
                break
            client.send_message(message)
    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
