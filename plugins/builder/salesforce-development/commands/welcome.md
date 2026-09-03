---
description: Display the Salesforce session banner — connected org, edition, API, project metadata stats, MCP servers. Auto-invoked at session start by the SessionStart hook.
allowed-tools:
  - Bash
---

The plugin paints the full Salesforce session banner — the HEADLESS logo lockup, connected org, edition and API, project metadata counts, platform MCP server status, and the position rail — directly to the user on the visible channel, in color: the same banner the session-start surface shows, so it is already shown. Do NOT run a command, redraw it, reproduce it in a fenced block, reformat it into a table, or restate it line by line. Add only a brief, welcoming one- or two-line read that orients the user to the single most useful next step given what the banner shows. Every hard fact — org, edition, API version, metadata counts, MCP status, current stage — comes only from that painted surface: present these facts faithfully, never invent, recompute, or substitute a remembered value, and when the surface omits a fact, say it is unknown.
