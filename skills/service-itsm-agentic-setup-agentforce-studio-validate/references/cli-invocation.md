# CLI invocation reference — service-itsm-agentic-setup-agentforce-studio-validate

This skill uses the **Salesforce CLI (`sf`)** as its only transport, and it is
**read-only**: it reads the *Agentforce for IT Service* Salesforce Go feature
toggles via one Connect API POST (`sf api request rest`), and a Node helper
script classifies the chosen agent path into a verdict. It **never enables** a
toggle — turning toggles on is owned by the separate write-capable skill
`service-itsm-agentic-setup-agentforce-studio-configure`, which this skill hands
off to on NOT-READY. It extracts no access tokens.

## Why `sf api request rest`, never curl + token

`sf api request rest` authenticates using the CLI's stored session for the
`--target-org` alias — the CLI mints/refreshes the token internally and never
exposes it. **Do not** do:

<!-- skill-validate: ignore -->
```bash
# FORBIDDEN — leaks a bearer token into shell context, bypasses the CLI session
TOKEN=$(sf org display --json -o <alias> | jq -r '.result.accessToken')
curl -H "Authorization: Bearer $TOKEN" https://.../connect/setup/discovery/features/status
```

Every call this skill makes is a plain `/services/data/v67.0/connect/...` Connect
API path, exactly what `sf api request rest` proxies. There is no reason to fall
back to curl.

## Why SF CLI (Connect API), not Headless360

The *Agentforce for IT Service* Go toggles are backed by real Connect API
features under `/connect/setup/discovery/`. Because a Connect equivalent exists,
the transport decision prefers SF CLI to avoid the `Headless360HostedMcpServer`
org-perm gate. (The only ITSM-adjacent pref that has *no* Connect equivalent —
the org-wide multi-agent orchestrator toggle — is out of this skill's scope and
would require Headless360 dispatch.)

## The feature toggles

The *Agentforce for IT Service* setup page (feature key
`service-cloud-agentforce-for-itsm`) has these child toggles. The `featureApiName`
column is what the API uses:

| UI toggle | featureApiName | Required for |
|-----------|----------------|--------------|
| Turn on Agentforce Studio | `sales-cloud-agent-studio` | both paths |
| Agentforce for IT Service | `service-cloud-agentforce-for-itsm` | both paths |
| IT Service Fulfiller Template | `service-cloud-it-fulfiller-agent` | fulfiller |
| IT Service Employee Template | `service-cloud-requestor-agent` | employee |
| Specialized Agent Templates for Employee | `service-cloud-it-service-employee-agent` | employee |

Dependency chain (enable order): `sales-cloud-einstein-generative-ai` →
`sales-cloud-agent-studio` → `service-cloud-agentforce-for-itsm` (parent) → the
child template toggles. The read response echoes this in `dependencyStatuses[]`.

## Target org, API version, and the `--json` rule

- **Target org**: always `--target-org <alias>` (or `-o <alias>`). Resolve from
  the user or the default org (`sf config get target-org`).
- **API version**: pinned in the URL path (`/services/data/v67.0/...`). Do not
  hand-edit below `metadata.minApiVersion` (`67.0`).
- **`--json`**: do **not** add `--json` to `sf api request rest` — it is
  unsupported on some Connect endpoints and errors; the raw stdout body is
  already JSON.

## Read — feature status (the one read this skill makes)

```bash
sf api request rest "/services/data/v67.0/connect/setup/discovery/features/status" \
  --method POST \
  --body '{"featureApiNames":["sales-cloud-agent-studio","service-cloud-agentforce-for-itsm","service-cloud-it-fulfiller-agent","service-cloud-requestor-agent","service-cloud-it-service-employee-agent"]}' \
  --target-org <alias> > /tmp/features-status.json 2>/tmp/features-status.err
echo $? > /tmp/features-status.exit
```

Capture the exit status (`$?`) rather than swallowing it with `|| true` — the
classifier uses it to separate a confirmed 404 (gate not wired → CANNOT-CONFIRM)
from an empty-body auth/permission/transport failure (→ ERROR, surface and stop).
It is safe to always request all five apiNames — the classifier only judges the
subset the chosen path requires. Response shape (abridged):

```json
{
  "items": [
    {
      "apiName": "service-cloud-it-fulfiller-agent",
      "status": "ENABLED",
      "enableBlockedReasons": [],
      "dependencyStatuses": [
        { "apiName": "sales-cloud-agent-studio", "status": "ENABLED", "enableBlockedReasons": [] }
      ]
    },
    { "apiName": "service-cloud-it-service-employee-agent", "status": "NOT_ENABLED", "enableBlockedReasons": [] }
  ]
}
```

- `status: "ENABLED"` ⇒ toggle on ⇒ **PASS**.
- `status: "NOT_ENABLED"` with empty `enableBlockedReasons` ⇒ toggle off ⇒ **FAIL**;
  the classifier lists it under `enableable` and attaches the enable route (which the
  hand-off skill uses — this skill only reports it, it does not call it).
- `status: "NOT_ENABLED"` with non-empty `enableBlockedReasons` ⇒ **FAIL** but
  **not** enableable — the classifier keeps it in `notEnabled`, omits it from
  `enableable`, and carries the blockers so the hand-off never queues a doomed enable.
- A missing item ⇒ **CANNOT-CONFIRM** for that toggle.
- A confirmed `404`/NOT_FOUND error body ⇒ whole read is **CANNOT-CONFIRM** (gate not wired).
- An empty body (CLI exited non-zero) or an auth/permission/unexpected error body ⇒
  whole read is **ERROR** — surface `rawError` and stop.

The single-feature GET `.../connect/setup/discovery/feature/{apiName}/summary`
returns the same status for one feature; the batch POST above is preferred so one
call covers the whole path.

## Enablement is a hand-off — this skill never POSTs an enable

This skill is read-only. When the verdict is NOT-READY, it names each disabled
toggle (the `notEnabled` list; `enableable` is the subset with no blockers) and
hands off to **`service-itsm-agentic-setup-agentforce-studio-configure`**, which
owns the write path `POST /connect/setup/discovery/feature/{apiName}/enable`
(idempotent, dependency-ordered — Einstein GenAI → Studio → the ITSM child
toggles). After the user runs that skill, re-read `features/status` here and
re-run the classifier to confirm the verdict flips to READY. Do **not** POST the
enable route from this skill — that would duplicate the configure skill's
responsibility and break the read-only contract the `validate` name promises.

## The classifier — `scripts/classify-readiness.mjs`

The deterministic verdict logic lives in the script, not in the workflow prose
(authoring standard A9). Invoke it with the captured file **and** the agent type,
using the skill's **absolute** directory (a bare `./scripts/...` won't resolve
against the CWD):

```bash
node "<skill_dir>/scripts/classify-readiness.mjs" /tmp/features-status.json <fulfiller|employee> "$(cat /tmp/features-status.exit)"
```

The third arg (the captured `$?`) is optional but recommended — it lets the
classifier distinguish an empty-body failure (ERROR) from a confirmed 404
(CANNOT-CONFIRM). Output (to stdout):

```json
{
  "agentType": "fulfiller | employee",
  "readState": "ok | not-wired | error",
  "features": { "<apiName>": { "status": "ENABLED|NOT_ENABLED|UNKNOWN", "signal": "PASS|FAIL|CANNOT-CONFIRM|ERROR", "enableBlockedReasons": [], "enableable": true, "enableRoute": "POST .../enable | null" } },
  "verdict": "READY | NOT-READY | CANNOT-CONFIRM | ERROR",
  "notEnabled": ["<apiName>", "..."],
  "enableable": ["<apiName>", "..."],
  "reasons": ["..."],
  "rawError": "null | <error snippet>"
}
```

Verdict rule (encoded in the script):
- A read failure that is **not** a confirmed 404 (empty body / auth / permission /
  unexpected shape) ⇒ `ERROR` — surface `rawError` and stop.
- Otherwise: any required toggle `FAIL` ⇒ `NOT-READY`; all required `PASS` ⇒
  `READY`; else (a `CANNOT-CONFIRM` with no `FAIL`) ⇒ `CANNOT-CONFIRM`.

`notEnabled` lists every `NOT_ENABLED` required toggle; `enableable` is the subset
with **no** `enableBlockedReasons` — the toggles the hand-off configure skill can
turn on straight away (the rest are blocked). `enableRoute` is informational only.
The script always exits `0` on a usable agent type; the verdict is in the payload.
A confirmed `404`/NOT_FOUND maps every feature to CANNOT-CONFIRM (never a throw);
an empty/auth/unexpected body maps to ERROR.

## Error taxonomy

- **Auth error / `401 Unauthorized`** — session expired or wrong alias. Re-run
  `sf org login web`; there is no token to refresh by hand.
- **`403 Forbidden`** — the user/org lacks the Agentforce license (`accessCheck`
  gate). Surface verbatim.
- **`404 Not Found`** on `features/status` — the feature-discovery surface is not
  wired on the org tier (expected on some scratch orgs). The classifier maps a
  confirmed 404/NOT_FOUND error body to CANNOT-CONFIRM.
- **`401 Unauthorized` / `403 Forbidden` / empty body / unexpected shape** —
  the classifier maps these to **ERROR** (not CANNOT-CONFIRM): surface `rawError`
  and stop. An unreadable org must not masquerade as a mere wiring gap.
- **`enableBlockedReasons` non-empty** on a toggle — an unmet dependency or a
  purchase/licensing gate; the classifier keeps the toggle in `notEnabled`,
  omits it from `enableable`, and reports the reason. Do not POST enable.

## Gotchas

| Issue | Resolution |
|-------|------------|
| `sf api request rest --json` errors | Don't pass `--json` — the raw stdout body is already JSON |
| Bare `./scripts/classify-readiness.mjs` "not found" | Use the skill's absolute `<skill_dir>` in the `node` invocation |
| Passing the file but no agent type | The classifier needs `<fulfiller\|employee>` as its 2nd arg — it exits 2 (usage) otherwise |
| Treating a 404 as a hard fail | A confirmed 404 is CANNOT-CONFIRM — report which toggle had no status, not a hard NOT-READY |
| Treating an auth/permission failure or empty body as CANNOT-CONFIRM | Pass `$?` as the 3rd classifier arg — an empty/auth/unexpected body is ERROR (surface `rawError`, stop); only a confirmed 404 is CANNOT-CONFIRM |
| Handing off a blocked toggle for enable | Hand off only the `enableable` toggles; a `notEnabled` toggle with `enableBlockedReasons` is excluded — report the blocker instead |
| POSTing the enable route from this skill | Never — this skill is read-only; enablement is owned by `service-itsm-agentic-setup-agentforce-studio-configure`. Hand off instead |
| Tempted to token+curl for "just a POST read" | Never — `sf api request rest` handles auth for `/services/data/...` paths |
| Checking `agentforce-studio/access/{product}` as the studio toggle | That endpoint is a product-entitlement check, not the feature toggle — use `sales-cloud-agent-studio` feature status instead |
