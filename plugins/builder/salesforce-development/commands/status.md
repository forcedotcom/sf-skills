---
description: Show the Salesforce project banner — connected org, edition, API, project metadata stats, and MCP server status.
allowed-tools:
  - Bash
---

Run the sf-context status command to print the current banner with org details, project metadata counts, git status (if applicable), and platform MCP server connection status:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context status
```

Output the result verbatim to the user, preserving the box-drawing characters and formatting.
