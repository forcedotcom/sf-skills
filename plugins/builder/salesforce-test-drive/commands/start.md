---
description: Start the Test Drive experience and take a Salesforce capability for an end-to-end drive against a connected org. Checks readiness, helps connect or provision an org, presents the menu, then choreographs the build live. Pass a test-drive id to launch one directly, or --instrument to record a DX-friction session log.
argument-hint: "[<test-drive-id>] [--instrument]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
  - Skill
  - Task
---

You are launching the **Test Drive engine** through `/salesforce-test-drive:start` — this plugin's
single command and entry point.

Parse `$ARGUMENTS`: an optional test-drive `id` to launch directly (skip the menu), and an optional
`--instrument` flag. Then read the engine and follow it **exactly, start to finish**:

```bash
echo "PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT}"
cat "${CLAUDE_PLUGIN_ROOT}/references/engine.md"
```

`PLUGIN_ROOT` echoed above is this plugin's absolute path, already resolved by Claude Code here in the
command. **Remember that value and pass it to the engine as `PLUGIN_ROOT`.** The engine reads its
catalog, prompts, and instrumentation spec from `<PLUGIN_ROOT>/…`; substitute this absolute path wherever
it does. Do **not** type the literal `${CLAUDE_PLUGIN_ROOT}` into a Bash command — that token only
resolves inside a command body like this one, not in the engine's text, and your Bash shell has no such
variable (it would expand to an empty string and break the path).

- If `$ARGUMENTS` named an `id`, run the engine with `SELECTED_DRIVE` set to that id (Step 3 skips the
  menu).
- Otherwise run the engine with `SELECTED_DRIVE` **empty** — Step 3 presents the catalog menu and lets
  the user choose.
- Pass the `--instrument` flag through to the engine's Step 5.

The engine owns all of the logic (companion check, toolchain preflight, org detection, tiered
provisioning, requirements gate, launch, handoff). Do not reimplement any of it here.
