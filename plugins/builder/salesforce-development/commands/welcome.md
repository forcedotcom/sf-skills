---
description: Display the Salesforce session banner — connected org, edition, API, project metadata stats, MCP servers. Auto-invoked at session start by the SessionStart hook.
allowed-tools:
  - Bash
---

Run the sf-context status command and output the result EXACTLY as printed (do not summarize, do not paraphrase, do not omit lines):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context status
```

Print the entire stdout verbatim, preserving the box-drawing characters, ASCII banner, and column alignment. Then add a one-line greeting on the next line: "Salesforce development mode active. Ask me about your org, generate metadata, deploy changes, or type /salesforce-development:status anytime for this view."

Do NOT add any other commentary, summary, or follow-up question.
