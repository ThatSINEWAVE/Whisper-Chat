<div align="center">

# Whisper Chat

![Banner](https://raw.githubusercontent.com/ThatSINEWAVE/Whisper-Chat/refs/heads/main/.github/SCREENSHOTS/Whisper-Chat.png)

Whisper Chat is a lightweight chat server with a web-based monitoring dashboard. This project is in **very early development** and is not yet ready for production use.

</div>

## Current Features

- Basic real-time chat functionality
- Web dashboard for monitoring connections and activity
- Simple client/server architecture using TCP sockets
- JSON-based message protocol
- Auto-logging of all chat activity
- Command-line client interface

<div align="center">

## ☕ [Support my work on Ko-Fi](https://ko-fi.com/thatsinewave)

</div>

## Project Structure

```
whisper-chat/
├── whisper_chat.py                 # Main server application (chat server + dashboard)
├── client.py                       # Command-line client implementation
├── templates/                      # Contains HTML templates for the dashboard
│   └── dashboard.html              # Dashboard template
├── static/                         # Stores static assets like CSS and JavaScript
│   ├── styles.css                  # Dashboard styling
│   └── dashboard.js                # Dashboard interactivity
├── site-data/                      # Metadata and icons for web browsers
│   ├── android-chrome-192x192.png  # Android Chrome icon (192x192)
│   ├── android-chrome-512x512.png  # Android Chrome icon (512x512)
│   ├── apple-touch-icon.png        # Apple touch icon for iOS devices
│   ├── favicon.ico                 # Standard favicon
│   ├── favicon-16x16.png           # Small favicon (16x16)
│   ├── favicon-32x32.png           # Standard favicon (32x32)
│   ├── icon-144x144.png            # Windows tile icon (144x144)
│   └── site.webmanifest            # Web app manifest file
└── logs/                           # Automatically generated chat logs
```

## Getting Started

### Requirements

- Python 3.6+
- Flask (server only)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/whisper-chat.git
   cd whisper-chat
   ```

2. Install dependencies for the server:
   ```
   pip install flask
   ```

### Running the Server

```
python whisper_chat.py
```

This will:
- Start the chat server on port 9999
- Launch the admin dashboard on port 8080
- Open your web browser to the dashboard

### Connecting as a Client

The client is a simple command-line application that connects to the Whisper Chat server:

```
python client.py
```

When you run the client:
1. Enter your username when prompted
2. Chat messages will appear in the terminal
3. Type your messages and press Enter to send
4. Type 'exit' to disconnect from the server

Example usage:
```
$ python client.py
Enter your username: Alice
Connecting to chat server...
Connected as Alice. Type 'exit' to quit.
[SYSTEM] Alice has joined the chat
Bob: Hello Alice!
Hello Bob!
[SYSTEM] Charlie has joined the chat
exit
Disconnecting...
```

## Client Protocol

The client and server communicate using a simple JSON-based protocol:

### Connect message

```json
{
    "type": "connect",
    "username": "username"
}
```

### Chat message

```json
{
    "type": "message",
    "username": "username",
    "content": "message text"
}
```

### Disconnect message

```json
{
    "type": "disconnect",
    "username": "username"
}
```

### System message (server to client)

```json
{
    "type": "system",
    "content": "system message text"
}
```

<div align="center">

## [Join my discord server](https://discord.gg/2nHHHBWNDw)

</div>

## Roadmap

Future development plans include:
- End-to-end encryption
- User authentication
- Private messaging
- Chat rooms/channels
- File sharing
- Mobile client applications
- GUI client application

## Contributing

As this project is in early development, please reach out before submitting pull requests. All contributions are welcome!

## License

This project is open-source and available under the [GPL-3.0 License](LICENSE)

## Disclaimer

This software is provided "as is" without warranty of any kind. Use at your own risk.