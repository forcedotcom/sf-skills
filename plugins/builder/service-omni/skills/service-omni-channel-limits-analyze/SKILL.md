---
name: service-omni-channel-limits-analyze
description: "Use to report Omni-Channel Pending Service Routing usage without changing the org: query the current PendingServiceRouting count, compare it with an admin-supplied maximum or a labeled routing-model reference default, and explain which live values are unavailable through supported APIs. TRIGGER when: check Omni-Channel limits, inspect PSR limits, analyze PendingServiceRouting usage, review pending routing capacity, or report queued work usage. Do not use to change limits or scrape Salesforce Setup."
allowed-tools: Bash Read Write Grep Glob
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-channel-inventory-analyze"
    - "service-omni-channel-setup-coordinate"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-channel-limits-analyze

Report the Pending Service Routing usage that can be obtained safely through supported customer-org APIs. The Salesforce **Setup → Omni-Channel → Limits** page is read-only and also displays internal values that are not exposed through REST, Tooling, Metadata, or Connect APIs. This skill reports the live PSR count and labels every non-verifiable value explicitly.

## Inputs

```bash
bash scripts/analyze.sh <org-alias> [--routing-model enhanced|legacy] [--max-psrs <integer>]
```

- `org-alias` is required and must already be authenticated with Salesforce CLI.
- `--routing-model` defaults to `enhanced`. It selects only the reference maximum used when `--max-psrs` is absent.
- `--max-psrs` accepts an administrator-provided maximum from 1 through 1,000,000. It is still labeled as not API-verified.

## Run

Invoke `scripts/analyze.sh` with the target org and rely on its JSON result for the live count, labeled comparison values, unavailable hourly values, and blocking details. The script invokes `sf org display` and `sf data query` internally; do not reproduce their query or calculation logic outside the script.

To verify the bundled script contract after a change, run `python3 scripts/tests/test_limits_analyze_contracts.py`; the test module loads its local `scripts/tests/_bootstrap.py` fixture automatically.

## Output contract

The script emits one JSON object:

- `skill`: `service-omni-channel-limits-analyze`
- `status`: `analyzed` or `blocked`
- `routing_model`: `enhanced` or `legacy`
- `metrics.current_pending_service_routings`: live count, comparison maximum, approximate percentage, and source labels
- `metrics.pending_service_routing_rate_per_hour`: unavailable live value, reference maximum, and source labels
- `caveats`: mandatory accuracy boundaries
- `blocking_issue`: actionable failure reason or `null`

If `PendingServiceRouting` cannot be queried, return `status: blocked`. Do not reinterpret an unavailable object, missing feature, or permission failure as zero usage.

## Boundaries

- Never scrape, replay, or submit the Visualforce Setup page. Its session state and controller are not a supported customer API.
- Never describe a reference default as the org's configured maximum.
- Never fabricate the live hourly rate or compute its utilization percentage.
- Never mutate routing, queues, agents, limits, or metadata.
- Treat the PSR count as a point-in-time snapshot that can change while work is routed.
- For a complete channel and routing inventory, use `service-omni-channel-inventory-analyze`.
- For a user-approved end-to-end Omni setup, hand off to `service-omni-channel-setup-coordinate`; this limits analyzer remains read-only.

## Reference

Read `references/api-notes.md` when explaining why the report cannot exactly reproduce every value on the Setup page.
