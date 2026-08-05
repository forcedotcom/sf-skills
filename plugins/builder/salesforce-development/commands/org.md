---
description: Show just the connected Salesforce org details — alias, edition, API version, instance URL, username.
allowed-tools:
  - Bash
---

Print the connected org info without the banner or project stats:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context status-org
```

Output the result verbatim, preserving the formatting.
