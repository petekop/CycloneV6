#!/usr/bin/env python3
"""Entry point for the macOS bundled Cyclone app.

Starts the Cyclone Flask server and opens the UI in the default browser.
"""

import threading
import time
import webbrowser

import cyclone_server


def _start_server():
    """Run the Cyclone Flask server."""
    cyclone_server.setup_logging()
    cyclone_server.app.run(debug=False, host="0.0.0.0", port=5050)


def main() -> None:
    """Start the server then open the UI."""
    server_thread = threading.Thread(target=_start_server)
    server_thread.start()
    # Give the server a moment to come up before opening the UI
    time.sleep(1)
    webbrowser.open("http://localhost:5050/boot")
    server_thread.join()


if __name__ == "__main__":
    main()
