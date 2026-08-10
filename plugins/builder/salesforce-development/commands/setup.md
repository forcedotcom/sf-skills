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

The output is a JSON object with a `tools` array (plus a `diagnostic` block on any critical failure).

**The banner is painted for you — do not reproduce it.** When `check-tools` runs, the plugin paints the framed **"Ready to build on Salesforce?"** banner deterministically on the visible channel (one status row per tool, the footer verdict, and the wayfinding footer), exactly like the SessionStart banner. Read the JSON for your own understanding, but do **NOT** reproduce, redraw, or re-render the banner — add only a short read of what it means for the user, then go to Phase 2.

**Only if you do not see the banner painted** (an older Claude Code build, or a paint fallback) render it yourself from the JSON, using the layout defined in the `platform-environment-validate` skill as the single source of truth. **Read `${CLAUDE_PLUGIN_ROOT}/skills/platform-environment-validate/SKILL.md` (Phase 1)** for the canonical frame, status-dot definitions, fixed row order, footer verdict, and wayfinding footer. In brief: one framed block, one row per tool with a 🔴/🟡/🟢/ℹ️ status dot in a fixed order, and a footer verdict — ` ✓ toolchain ready` when there are no 🔴/🟡 rows, or ` ⚠ <N> need attention · <M> ready` otherwise — then the "You don't memorize commands here." wayfinding block ending in a context-aware `Next: <action> → "<phrase>"` line. A setup is "all green" when there are no 🔴 or 🟡 rows; ℹ️ rows never count against it.

**Deterministic results — do NOT override a failure.** The JSON report is the authoritative result. If a tool reports 🔴/🟡, render it as-is; never re-run the check a different way and present the result as 🟢. When the report includes a `diagnostic` block (attached on any critical failure), surface it — it carries platform, active shell, working directory, plugin root, and the resolved executable paths, and is secret-free by design.

Note: the Code Analyzer plugin is a JIT ("just-in-time") plugin — if it is registered but not yet physically installed, `check-tools` reports it 🟢 with a note that it auto-installs on first `sf code-analyzer` run. That is expected and not a problem.

## Phase 2: Install / Update

**If all green:** confirm setup is complete — the user is ready to develop.

**If any 🔴/🟡 items exist:** offer to help. For each item the user wants to fix, show the correct install/update command for their OS and ask them to confirm before running it — do **not** run install commands automatically.

For the full guided install/update flow (per-tool commands by OS, PATH-restart guidance, source-tracking enablement), see the `platform-environment-validate` skill.

## Notes

- After installing a tool that modifies PATH (Node.js, SF CLI), the user may need to restart Claude Code for the change to take effect.
- For org authentication issues (expired session, wrong org), run `/salesforce-development:login`.
- For a quick org/project banner rather than a prerequisite scan, run `/salesforce-development:status`.
