# Mermaid Preview Server

A lightweight HTTP server with live reload for previewing Mermaid diagrams in your browser.

## Features

- **Live Reload**: Browser automatically refreshes when your diagram file changes
- **Zero Dependencies**: Pure Python stdlib - no pip install required
- **Background Mode**: Server runs in background, doesn't block your terminal
- **Dark Mode**: Automatically matches your system theme preference
- **Copy & Download**: Copy Mermaid code or download as SVG directly from browser

## Quick Start

```bash
# Start the server (opens browser automatically)
python mermaid_preview.py start --file /tmp/my-diagram.mmd

# Check if server is running
python mermaid_preview.py status

# Stop the server
python mermaid_preview.py stop
```

## Usage

### Starting the Server

```bash
python mermaid_preview.py start --file <path-to-mermaid-file>
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--file`, `-f` | Mermaid file to watch | `/tmp/mermaid-preview.mmd` |
| `--port`, `-p` | Server port | `8765` |
| `--no-browser` | Don't auto-open browser | `false` |
| `--pid-file` | PID file location | `/tmp/mermaid-preview.pid` |

### Stopping the Server

```bash
python mermaid_preview.py stop
```

### Checking Status

```bash
python mermaid_preview.py status
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Tab                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Mermaid Diagram (rendered)                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↑                                    │
│            SSE: http://localhost:8765/events                 │
│              (receives "reload" events)                      │
└─────────────────────────────────────────────────────────────┘
                          ↑
┌─────────────────────────────────────────────────────────────┐
│              mermaid_preview.py (background)                 │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │             HTTP Server :8765                          │  │
│  │  GET /           → Serves rendered HTML                │  │
│  │  GET /events     → SSE stream for live reload          │  │
│  └───────────────────────────────────────────────────────┘  │
│                             ↑                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  File Watcher (polls every 500ms)                      │  │
│  │  Triggers reload when file mtime changes               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↑
                 /tmp/mermaid-preview.mmd
                     (your diagram file)
```

1. **HTTP Server** serves the HTML page with your Mermaid diagram
2. **File Watcher** monitors your diagram file for changes (polling mtime every 500ms)
3. **SSE (Server-Sent Events)** pushes "reload" events to the browser when file changes
4. **Browser** automatically refreshes to show the updated diagram

## Integration with sf-diagram Skill

When using the sf-diagram skill, you can request a preview:

1. Ask sf-diagram to create a diagram
2. Say "preview this diagram" or "show me the preview"
3. The skill will:
   - Save the diagram to `/tmp/mermaid-preview.mmd`
   - Start the preview server
   - Give you the URL: `http://localhost:8765`
4. As you iterate on the diagram, the browser auto-refreshes
5. When done, say "stop preview" or run `python mermaid_preview.py stop`

## Browser Features

### Copy Mermaid Code
Click the "Copy Mermaid Code" button to copy the raw Mermaid syntax to your clipboard.

### Download SVG
Click "Download SVG" to save the rendered diagram as an SVG file.

### Connection Status
The status indicator shows whether you're connected to the live reload server:
- **● Connected** (green): Live reload is active
- **○ Disconnected** (red): Server connection lost, will auto-reconnect

## Troubleshooting

### Port Already in Use

```bash
# Check if something is using port 8765
lsof -i :8765

# Use a different port
python mermaid_preview.py start --file diagram.mmd --port 8766
```

### Server Won't Start

```bash
# Remove stale PID file
rm /tmp/mermaid-preview.pid

# Try starting again
python mermaid_preview.py start --file diagram.mmd
```

### Browser Doesn't Auto-Open

The `--no-browser` flag prevents auto-opening. To manually open:
1. Start server with `python mermaid_preview.py start --file diagram.mmd`
2. Open `http://localhost:8765` in your browser

### Live Reload Not Working

1. Check the connection status in the browser (should be "Connected")
2. Verify the file path is correct (shown in the browser)
3. Make sure you're saving the file (not just editing)
4. Try refreshing the browser manually

## Requirements

- Python 3.7+
- macOS or Linux (uses `os.fork()` for background mode)
- Modern browser with SSE support (all major browsers)

## License

MIT License
