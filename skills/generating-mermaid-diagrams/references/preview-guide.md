<!-- Parent: generating-mermaid-diagrams/SKILL.md -->
# Mermaid Preview Server Guide

After generating the diagram, offer the user a localhost preview for real-time iteration.

## Start Preview

1. Save Mermaid code to temporary file:
   ```
   Write: /tmp/mermaid-preview.mmd
   [Mermaid code content]
   ```

2. Start preview server (runs in background):
   ```bash
   # From installed skill folder:
   python ~/.claude/skills/generating-mermaid-diagrams/scripts/mermaid_preview.py start --file /tmp/mermaid-preview.mmd

   # Or from project folder (if working locally):
   python [project-root]/skills/generating-mermaid-diagrams/scripts/mermaid_preview.py start --file /tmp/mermaid-preview.mmd
   ```

3. Provide URL to user:
   > **Preview available**: http://localhost:8765
   >
   > The browser will auto-reload when you update the diagram.

## Iteration Workflow

- User views diagram in browser
- User requests changes ("make boxes pink", "add another node")
- You update `/tmp/mermaid-preview.mmd` using the Write tool
- Browser auto-reloads with new diagram (via SSE)
- Repeat until user is satisfied

## Stop Preview

When user is done:
```bash
python ~/.claude/skills/generating-mermaid-diagrams/scripts/mermaid_preview.py stop
```

## Preview Server Features

- Live reload via Server-Sent Events (SSE)
- Dark/light theme auto-detection
- Copy Mermaid code button
- Download as SVG button
- Connection status indicator
