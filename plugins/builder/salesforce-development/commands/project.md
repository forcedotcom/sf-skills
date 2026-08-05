---
description: Show just the local SFDX project metadata stats — Apex/triggers/LWC/Aura/objects/perm sets/flows counts and git status.
allowed-tools:
  - Bash
---

Print the local project metadata summary without the banner or org info:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context status-project
```

Output the result verbatim, preserving the formatting.
