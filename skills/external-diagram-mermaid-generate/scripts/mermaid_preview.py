#!/usr/bin/env python3
"""
Mermaid Diagram Preview Server

A lightweight HTTP server with live reload for previewing Mermaid diagrams.
Uses Server-Sent Events (SSE) for instant browser refresh on file changes.

Usage:
    python mermaid_preview.py start --file diagram.mmd    # Start server
    python mermaid_preview.py stop                         # Stop server
    python mermaid_preview.py status                       # Check if running

Options:
    --port PORT       Server port (default: 8765)
    --no-browser      Don't auto-open browser
    --pid-file PATH   PID file location (default: /tmp/mermaid-preview.pid)

Examples:
    # Start preview for a diagram file
    python mermaid_preview.py start --file /tmp/my-diagram.mmd

    # Check server status
    python mermaid_preview.py status

    # Stop the server
    python mermaid_preview.py stop

License: MIT
"""

import argparse
import http.server
import os
import signal
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional, Set
from urllib.parse import urlparse

# Default configuration
DEFAULT_PORT = 8765
DEFAULT_PID_FILE = "/tmp/mermaid-preview.pid"
DEFAULT_WATCHED_FILE = "/tmp/mermaid-preview.mmd"
POLL_INTERVAL = 0.5  # seconds

# Global state for file watching
_watched_file: Optional[str] = None
_last_mtime: float = 0
_sse_clients: Set = set()
_file_changed_event = threading.Event()

# HTML template with SSE live reload
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mermaid Preview - sf-diagram</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    :root {
      --bg: #f8fafc;
      --text: #1f2937;
      --card: #ffffff;
      --border: #e2e8f0;
      --accent: #3b82f6;
      --success: #22c55e;
      --error: #ef4444;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #0f172a;
        --text: #f1f5f9;
        --card: #1e293b;
        --border: #334155;
        --accent: #60a5fa;
      }
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 1.5rem;
    }
    .container { max-width: 1400px; margin: 0 auto; }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
    }
    .header h1 { font-size: 1.5rem; font-weight: 600; }
    .status {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
    }
    .status-dot.disconnected { background: var(--error); }
    .file-info {
      font-size: 0.875rem;
      opacity: 0.7;
      margin-bottom: 1rem;
    }
    .file-info code {
      background: var(--card);
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      border: 1px solid var(--border);
    }
    .diagram-container {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 2rem;
      overflow-x: auto;
    }
    .mermaid {
      display: flex;
      justify-content: center;
    }
    .toolbar {
      display: flex;
      gap: 0.5rem;
      margin-top: 1rem;
    }
    button {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--card);
      color: var(--text);
      cursor: pointer;
      font-size: 0.875rem;
      transition: all 0.15s;
    }
    button:hover {
      background: var(--bg);
      border-color: var(--accent);
    }
    button:active { transform: scale(0.98); }
    .toast {
      position: fixed;
      bottom: 1rem;
      right: 1rem;
      padding: 0.75rem 1rem;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.2s;
    }
    .toast.show {
      opacity: 1;
      transform: translateY(0);
    }
    .footer {
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      font-size: 0.75rem;
      opacity: 0.5;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="container">
    <header class="header">
      <h1>Mermaid Preview</h1>
      <div class="status">
        <span class="status-dot" id="statusDot"></span>
        <span id="statusText">Connected</span>
      </div>
    </header>

    <p class="file-info">Watching: <code id="filePath">{{FILE_PATH}}</code></p>

    <div class="diagram-container">
      <pre class="mermaid" id="diagram">{{MERMAID_CODE}}</pre>
    </div>

    <div class="toolbar">
      <button onclick="copyCode()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        Copy Mermaid Code
      </button>
      <button onclick="downloadSVG()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        Download SVG
      </button>
      <button onclick="location.reload()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"></polyline>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
        </svg>
        Refresh
      </button>
    </div>

    <footer class="footer">
      sf-diagram preview server | Port {{PORT}}
    </footer>
  </div>

  <div class="toast" id="toast"></div>

  <script>
    // Store raw mermaid code for copy
    const rawMermaidCode = `{{MERMAID_CODE_ESCAPED}}`;

    // Initialize Mermaid
    mermaid.initialize({
      startOnLoad: true,
      theme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'default',
      securityLevel: 'loose'
    });

    // SSE for live reload
    function connectSSE() {
      const events = new EventSource('/events');

      events.onopen = () => {
        document.getElementById('statusDot').classList.remove('disconnected');
        document.getElementById('statusText').textContent = 'Connected';
      };

      events.onmessage = (e) => {
        if (e.data === 'reload') {
          showToast('File changed, reloading...');
          setTimeout(() => location.reload(), 300);
        }
      };

      events.onerror = () => {
        document.getElementById('statusDot').classList.add('disconnected');
        document.getElementById('statusText').textContent = 'Disconnected';
        // Attempt to reconnect after 3 seconds
        setTimeout(connectSSE, 3000);
      };
    }

    connectSSE();

    // Copy mermaid code to clipboard
    function copyCode() {
      navigator.clipboard.writeText(rawMermaidCode).then(() => {
        showToast('Copied to clipboard!');
      }).catch(() => {
        showToast('Failed to copy');
      });
    }

    // Download as SVG
    function downloadSVG() {
      const svg = document.querySelector('.mermaid svg');
      if (!svg) {
        showToast('No SVG to download');
        return;
      }

      const svgData = new XMLSerializer().serializeToString(svg);
      const blob = new Blob([svgData], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = 'diagram.svg';
      a.click();

      URL.revokeObjectURL(url);
      showToast('SVG downloaded!');
    }

    // Toast notification
    function showToast(message) {
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2000);
    }
  </script>
</body>
</html>
"""


class MermaidPreviewHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for Mermaid preview server."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            self._serve_html()
        elif path == "/events":
            self._serve_sse()
        else:
            self.send_error(404, "Not Found")

    def _serve_html(self):
        """Serve the HTML page with the Mermaid diagram."""
        global _watched_file

        # Read the mermaid file
        mermaid_code = ""
        if _watched_file and os.path.exists(_watched_file):
            try:
                with open(_watched_file, "r") as f:
                    mermaid_code = f.read().strip()
            except Exception as e:
                mermaid_code = f"flowchart TB\n    Error[Error reading file: {e}]"
        else:
            mermaid_code = "flowchart TB\n    A[No file specified]\n    A --> B[Use --file option]"

        # Escape for JavaScript string
        mermaid_escaped = mermaid_code.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

        # Generate HTML
        html = HTML_TEMPLATE
        html = html.replace("{{FILE_PATH}}", _watched_file or "No file")
        html = html.replace("{{MERMAID_CODE}}", mermaid_code)
        html = html.replace("{{MERMAID_CODE_ESCAPED}}", mermaid_escaped)
        html = html.replace("{{PORT}}", str(self.server.server_address[1]))

        # Send response
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(html.encode()))
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_sse(self):
        """Serve Server-Sent Events for live reload."""
        global _file_changed_event

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Send initial connection event
        self.wfile.write(b"data: connected\n\n")
        self.wfile.flush()

        # Keep connection open and send reload events
        try:
            while True:
                # Wait for file change event or timeout
                changed = _file_changed_event.wait(timeout=POLL_INTERVAL)
                if changed:
                    _file_changed_event.clear()
                    self.wfile.write(b"data: reload\n\n")
                    self.wfile.flush()
                else:
                    # Send keepalive comment
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected


def file_watcher():
    """Background thread that watches the file for changes."""
    global _watched_file, _last_mtime, _file_changed_event

    while True:
        try:
            if _watched_file and os.path.exists(_watched_file):
                current_mtime = os.path.getmtime(_watched_file)
                if current_mtime > _last_mtime:
                    _last_mtime = current_mtime
                    _file_changed_event.set()
        except Exception:
            pass

        time.sleep(POLL_INTERVAL)


def run_server_foreground(file_path: str, port: int, pid_file: str):
    """Run server in foreground (called by daemon subprocess)."""
    global _watched_file, _last_mtime

    _watched_file = file_path
    _last_mtime = os.path.getmtime(_watched_file) if os.path.exists(_watched_file) else 0

    # Write PID file
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    # Write info file
    try:
        with open(f"{pid_file}.info", "w") as f:
            f.write(f"PID: {os.getpid()}\nPort: {port}\nFile: {_watched_file}\n")
    except:
        pass

    # Ignore SIGHUP so we survive terminal close
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    # Start file watcher thread
    watcher_thread = threading.Thread(target=file_watcher, daemon=True)
    watcher_thread.start()

    # Start HTTP server
    server = http.server.HTTPServer(("", port), MermaidPreviewHandler)

    # Handle graceful shutdown
    def shutdown_handler(signum, frame):
        server.shutdown()
        if os.path.exists(pid_file):
            os.remove(pid_file)
        if os.path.exists(f"{pid_file}.info"):
            os.remove(f"{pid_file}.info")
        os._exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)
        if os.path.exists(f"{pid_file}.info"):
            os.remove(f"{pid_file}.info")


def start_server(file_path: str, port: int, no_browser: bool, pid_file: str):
    """Start the preview server as a detached background process."""
    import subprocess

    # Check if already running
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            # Check if process is still running
            os.kill(old_pid, 0)
            print(f"Server already running (PID: {old_pid})")
            print(f"Use 'python {sys.argv[0]} stop' to stop it first")
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            # Process not running, clean up stale PID file
            os.remove(pid_file)
            if os.path.exists(f"{pid_file}.info"):
                os.remove(f"{pid_file}.info")

    # Resolve file path
    abs_file_path = os.path.abspath(file_path)

    # Create file if it doesn't exist
    if not os.path.exists(abs_file_path):
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        with open(abs_file_path, "w") as f:
            f.write("flowchart TB\n    A[Edit this file]\n    A --> B[Browser will reload]")

    # Launch server as completely detached subprocess
    script_path = os.path.abspath(__file__)
    cmd = [
        sys.executable,
        script_path,
        "_run",  # Internal command
        "--file", abs_file_path,
        "--port", str(port),
        "--pid-file", pid_file,
    ]

    # Use nohup-like approach: redirect all IO to /dev/null, start new session
    with open("/dev/null", "r") as devnull_in, \
         open("/dev/null", "w") as devnull_out:
        process = subprocess.Popen(
            cmd,
            stdin=devnull_in,
            stdout=devnull_out,
            stderr=devnull_out,
            start_new_session=True,  # Detach from terminal
            close_fds=True,
        )

    # Wait briefly for server to start and write PID file
    time.sleep(0.3)

    # Verify server started
    if os.path.exists(pid_file):
        with open(pid_file, "r") as f:
            daemon_pid = f.read().strip()
        print(f"Mermaid Preview Server started!")
        print(f"  URL:     http://localhost:{port}")
        print(f"  File:    {abs_file_path}")
        print(f"  PID:     {daemon_pid}")
        print()
        print(f"Stop with: python {sys.argv[0]} stop")

        # Open browser
        if not no_browser:
            time.sleep(0.3)
            webbrowser.open(f"http://localhost:{port}")
    else:
        print("Warning: Server may not have started correctly")
        print(f"Check: python {sys.argv[0]} status")


def stop_server(pid_file: str):
    """Stop the preview server."""
    if not os.path.exists(pid_file):
        print("Server not running (no PID file found)")
        return

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        os.kill(pid, signal.SIGTERM)
        print(f"Server stopped (PID: {pid})")

        # Clean up PID file
        if os.path.exists(pid_file):
            os.remove(pid_file)

    except ProcessLookupError:
        print("Server not running (process not found)")
        os.remove(pid_file)
    except ValueError:
        print("Invalid PID file")
        os.remove(pid_file)


def server_status(pid_file: str):
    """Check server status."""
    if not os.path.exists(pid_file):
        print("Server status: STOPPED")
        return

    try:
        with open(pid_file, "r") as f:
            pid = int(f.read().strip())

        os.kill(pid, 0)  # Check if process exists
        print(f"Server status: RUNNING (PID: {pid})")

        # Try to read additional info
        info_file = f"{pid_file}.info"
        if os.path.exists(info_file):
            with open(info_file, "r") as f:
                for line in f:
                    if line.startswith("Port:"):
                        port = line.split(":")[1].strip()
                        print(f"  URL: http://localhost:{port}")
                    elif line.startswith("File:"):
                        file_path = line.split(":", 1)[1].strip()
                        print(f"  File: {file_path}")
        else:
            print(f"  URL: http://localhost:{DEFAULT_PORT}")

    except ProcessLookupError:
        print("Server status: STOPPED (stale PID file)")
        os.remove(pid_file)
        if os.path.exists(f"{pid_file}.info"):
            os.remove(f"{pid_file}.info")
    except ValueError:
        print("Server status: UNKNOWN (invalid PID file)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Mermaid Diagram Preview Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Start server:    python mermaid_preview.py start --file diagram.mmd
  Stop server:     python mermaid_preview.py stop
  Check status:    python mermaid_preview.py status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the preview server")
    start_parser.add_argument(
        "--file", "-f", default=DEFAULT_WATCHED_FILE, help=f"Mermaid file to watch (default: {DEFAULT_WATCHED_FILE})"
    )
    start_parser.add_argument("--port", "-p", type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")
    start_parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    start_parser.add_argument("--pid-file", default=DEFAULT_PID_FILE, help=f"PID file location (default: {DEFAULT_PID_FILE})")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the preview server")
    stop_parser.add_argument("--pid-file", default=DEFAULT_PID_FILE, help=f"PID file location (default: {DEFAULT_PID_FILE})")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check server status")
    status_parser.add_argument("--pid-file", default=DEFAULT_PID_FILE, help=f"PID file location (default: {DEFAULT_PID_FILE})")

    # Internal run command (used by start to spawn daemon)
    run_parser = subparsers.add_parser("_run", help=argparse.SUPPRESS)
    run_parser.add_argument("--file", "-f", required=True)
    run_parser.add_argument("--port", "-p", type=int, required=True)
    run_parser.add_argument("--pid-file", required=True)

    args = parser.parse_args()

    if args.command == "start":
        start_server(args.file, args.port, args.no_browser, args.pid_file)
    elif args.command == "stop":
        stop_server(args.pid_file)
    elif args.command == "status":
        server_status(args.pid_file)
    elif args.command == "_run":
        # Internal: run server in foreground (called by start as detached process)
        run_server_foreground(args.file, args.port, args.pid_file)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
