---
description: Turn plugin usage telemetry on or off, or show its current status (what's collected, machine id, buffered events).
allowed-tools:
  - Bash
---

Manage usage telemetry for the salesforce-development plugin. Default is ON; this is a true hard-off when disabled (nothing captured, buffered, or sent) and honors `SF_DISABLE_TELEMETRY` / `DO_NOT_TRACK`.

If the user asked to turn it **off**:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context telemetry off
```

If the user asked to turn it **on**:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context telemetry on
```

Otherwise show current **status**:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context telemetry status
```

Output the result verbatim to the user.
