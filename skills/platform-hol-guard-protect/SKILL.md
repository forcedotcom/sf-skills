---
name: platform-hol-guard-protect
description: "Use this skill when a local coding agent is about to run state-changing Salesforce CLI, metadata, deployment, org-configuration, or data-operation commands and the user wants HOL Guard runtime protection before execution. It installs and invokes HOL Guard on a detected supported agent harness while keeping Salesforce authentication, org targeting, permissions, native confirmations, validation, and post-change verification authoritative."
metadata:
  version: "1.0"
  domains: ["Platform"]
---

# Protecting Salesforce Agent Work with HOL Guard

Use HOL Guard as a local pre-execution boundary around a supported coding-agent harness before that agent performs state-changing Salesforce work. This skill adds a runtime protection layer; it does not replace Salesforce permissions, CLI behavior, deployment validation, backups, tests, or review requirements.

## When to Use

Use this skill before agent-driven work that can mutate Salesforce state, including:

- `sf project deploy` and other metadata deployments;
- destructive or state-changing `sf` commands;
- org configuration, permission, package, or environment changes;
- data import, update, delete, or bulk mutation workflows;
- scripts or shell commands that can change Salesforce resources or credentials.

Do not use this skill as a substitute for Salesforce-native authorization or as proof that a command is safe. HOL Guard protects the supported local coding-agent harness; it does not run inside Salesforce services or intercept server-side Salesforce execution.

## Set Up the Protected Harness

Install the maintained HOL Guard CLI, discover the exact supported harness identifier, initialize Guard, install the integration, and verify it before doing mutation work:

```bash
pipx install hol-guard
hol-guard detect --json
hol-guard bootstrap
hol-guard install <detected-harness>
hol-guard run <detected-harness> --dry-run
hol-guard doctor <detected-harness> --json
```

Use the harness identifier returned by `hol-guard detect --json`. Do not guess or maintain a separate adapter list.

After the dry run and doctor checks succeed, start the protected agent session with:

```bash
hol-guard run <detected-harness>
```

Run the Salesforce workflow only from that protected session.

## Execution Rules

Before a mutation:

1. Confirm the intended Salesforce org or environment using the Salesforce CLI and existing project guidance.
2. Prefer read-only inspection, validation, previews, or dry runs when Salesforce supports them.
3. Keep Salesforce permissions, org targeting, deployment checks, tests, and human approval requirements authoritative.
4. Execute the state-changing command only from the HOL Guard-protected harness.
5. If Guard denies, requires review, times out, returns malformed output, or is unavailable, stop the protected mutation. Do not retry the same action by launching an unprotected agent session.
6. After an allowed mutation, verify the resulting state with Salesforce-native read-back, tests, deployment status, or other project-required checks.

## Inspection vs Enforcement

`hol-guard command test` is useful for side-effect-free command inspection, but it is not a substitute for Guard-owned harness enforcement and must not be presented as the final Salesforce authorization decision.

For an actual protected workflow, use the installed harness integration and `hol-guard run <detected-harness>`.

## Boundary

- HOL Guard is the local agent-runtime protection layer.
- Salesforce authentication, authorization, org targeting, API limits, deployment semantics, and server-side controls remain authoritative.
- A HOL Guard allow decision never overrides a Salesforce denial or project review requirement.
- A Salesforce command being syntactically valid does not override a Guard deny or review-required state.
- Do not claim dedicated HOL Guard classification for a Salesforce-specific command unless that behavior has been independently verified.

## Verify

Before declaring the workflow complete:

- confirm `hol-guard doctor <detected-harness> --json` reports a healthy installed integration;
- confirm the state-changing action was executed from the protected harness;
- verify the resulting Salesforce state using the repository's existing Salesforce skills and native tooling;
- record any required deployment, test, or review evidence without exposing secrets, access tokens, or credentials.

HOL Guard source: https://github.com/hashgraph-online/hol-guard
