---
description: Turn uninstalled-plugin recommendations on or off, tune how readily they trigger, or show current status.
allowed-tools:
  - Bash
---

Manage this plugin's uninstalled-plugin recommendation sensitivity — how readily it proposes an uninstalled Salesforce plugin that matches your task. Default is `standard`; `off` is a true hard-off (no recommendation on any surface: SessionStart, prompt submission, the bypass gate, or the discovery command) and honors `SF_DISABLE_PLUGIN_MATCH`.

Named levels, from least to most readily triggered: `off`, `low` (threshold 6.0), `standard` (threshold 3.5, default), `high` (threshold 3.0). `high` sensitivity needs the *least* evidence before proposing a plugin, `low` needs the *most* — same relationship as a smoke detector's sensitivity dial.

A custom number from `1.0` to `10.0` is also accepted for finer control, on that same threshold scale: it is compared directly against the match score, so a *lower* number triggers *more* readily (more sensitive) and a *higher* number triggers *less* readily (less sensitive, more evidence required). It is easy to get this backwards — "high" sensitivity is the low end of the number range (3.0), not the high end.

If the user asked to turn it **off**:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context plugin-match-config off
```

If the user asked to turn it **on** (reset to the plugin's default):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context plugin-match-config on
```

If the user asked to **set** a level or custom number (e.g. `low`, `high`, or `7.5`):

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context plugin-match-config set <value>
```

Otherwise show current **status**:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context plugin-match-config status
```

Output the result verbatim to the user.
