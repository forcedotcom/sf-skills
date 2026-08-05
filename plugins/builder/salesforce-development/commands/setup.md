---
description: Validate the local Salesforce development environment — scan required tools (SF CLI, Code Analyzer, Node, NPM, Git, MCP, Source Tracking) with 🔴/🟡/🟢 status and offer guided install/update.
allowed-tools:
  - Bash
  - Read
---

Run the tool prerequisite scan and render an actionable status report.

## Phase 1: Scan

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context check-tools
```

The output is a JSON object with a `tools` array. Parse it and render a report grouped by severity:

```
=========================

🔴 Critical (N):
   <tool>: <message>

🟡 Warnings (N):
   <tool>: <message>

🟢 Successfully Configured (N):
   <tool> <version>

ℹ️ Informational (N):
   <tool>: <message>

=========================
```

**Status definitions:**
- 🔴 Critical (`critical`) — missing or below minimum; development cannot proceed without it
- 🟡 Warning (`warn`) — installed but outdated, non-LTS, or misconfigured
- 🟢 OK (`ok`) — installed and meets all requirements
- ℹ️ Info (`info`) — a contextual note that cannot be auto-verified (e.g. MCP process health); does **not** count against an "all green" result

A setup is "all green" when there are no 🔴 or 🟡 rows.

**Deterministic results — do NOT override a failure.** The JSON report is the authoritative result. If a tool reports 🔴/🟡, report it as-is; never re-run the check a different way and present the result as 🟢. When the report includes a `diagnostic` block (attached on any critical failure), surface it — it carries platform, active shell, working directory, plugin root, and the resolved executable paths, and is secret-free by design.

Note: the Code Analyzer plugin is a JIT ("just-in-time") plugin — if it is registered but not yet physically installed, `check-tools` reports it 🟢 with a note that it auto-installs on first `sf code-analyzer` run. That is expected and not a problem.

## Phase 2: Install / Update

**If all green:** confirm setup is complete — the user is ready to develop.

**If any 🔴/🟡 items exist:** offer to help. For each item the user wants to fix, show the correct install/update command for their OS and ask them to confirm before running it — do **not** run install commands automatically.

For the full guided install/update flow (per-tool commands by OS, PATH-restart guidance, source-tracking enablement), see the `platform-environment-validate` skill.

## Notes

- After installing a tool that modifies PATH (Node.js, SF CLI), the user may need to restart Claude Code for the change to take effect.
- For org authentication issues (expired session, wrong org), run `/salesforce-development:login`.
- For a quick org/project banner rather than a prerequisite scan, run `/salesforce-development:status`.
