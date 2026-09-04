# AHM Alerts Reference — Agent Health Monitoring Data Alerts

End-to-end procedures for creating, listing, deleting, and inspecting **Agent Health Monitoring (AHM)** data alerts, and for verifying the metric values behind them. This is the same functionality the AHM Setup UI performs at `/lightning/n/standard-AgentforceStudio?c__nav=alerts`, but driven entirely from the `sf` CLI.

Use this reference when the user wants to:

- Create / list / delete an AHM alert on an agent metric (escalation rate, deflection rate, etc.)
- Understand why an alert isn't firing
- Inspect triggered alert notifications (trigger history)
- Discover the alertable SDMs, metrics, and agent filter values on an org

---

## Contents

1. [CLI-first — how commands are expressed here](#cli-first--how-commands-are-expressed-here)
2. [The endpoint: `tableau/dataAlerts`](#the-endpoint-tableaudataalerts)
3. [List and describe alerts](#list-and-describe-alerts)
4. [Prerequisite: confirm the three alertable SDMs](#prerequisite-for-creating-alerts-confirm-the-three-alertable-sdms)
5. [Enumerate `_mtc` metrics and screen for time-grain fit](#enumerate-_mtc-metrics-and-screen-for-time-grain-fit)
6. [List the agents available for alert filters](#list-the-agents-available-for-alert-filters)
7. [Create an alert](#create-an-alert) — POST vs GET field names, `filterContext`, thresholds, full schema, enums, troubleshooting
8. [Update an alert](#update-an-alert) (not yet available — delete + recreate)
9. [Delete an alert](#delete-an-alert)
10. [Trigger history — inspect triggered notifications](#trigger-history--inspect-triggered-notifications)
11. [Verify metric value via Semantic Engine Gateway](#verify-metric-value-via-semantic-engine-gateway-condensed)
12. [Global troubleshooting](#global-troubleshooting)

---

## CLI-first — how commands are expressed here

Every operation is expressed through **`sf api request rest`**, which authenticates and executes with the org credentials the CLI already holds (`-o <org>`).

```bash
# Generic shape used throughout this reference
sf api request rest "<path>" -o <org>                          # GET
sf api request rest "<path>" -X POST -H "Content-Type: application/json" -b "@$body" -o <org>
sf api request rest "<path>/<id>" -X DELETE -o <org>
```

`sf api request rest` supports `-X/--method` (GET|POST|PUT|PATCH|DELETE|…), `-H/--header`, and `-b/--body` (`@file` to read a file, `-` for stdin, `""` for empty). Pipe the output to `python3 -m json.tool` to pretty-print.

> **Request bodies go in a private temp file — never a fixed `/tmp/<name>.json`.** The POST bodies below carry org data (SDM/agent names, user IDs, alert config). A predictable, world-readable path in the shared `/tmp` namespace invites info disclosure, symlink clobbering, and a TOCTOU swap between the `cat >` write and the `-b @file` read. Create a per-invocation `0600` file, pass it, and remove it on exit:
>
> ```bash
> body=$(mktemp) && chmod 600 "$body"
> trap 'rm -f "$body"' EXIT
> # cat > "$body" <<'JSON' … then: -b "@$body"
> ```
>
> Every heredoc example below assumes this `body=$(mktemp)` idiom (reuse the same `trap` for the run) and writes to `"$body"` rather than a literal `/tmp/*.json`.

> **Notes.**
> - **The org must already be authenticated — these commands do not launch a login.** Every call uses the credentials the CLI already holds for `-o <org>`. Pre-flight with `sf org display --target-org <org>` (or `sf org list`); if the alias is missing/unauthenticated, `sf` fails with `No authorization information found for <alias>` rather than prompting. Authenticate with `sf org login web --alias <alias>` — a browser flow the **user** runs (an agent can't complete it; in Claude Code prefix the command with `!`). An **expired** token auto-refreshes on the next call; a **missing/removed** auth does not.
> - There is **no dedicated `sf agent alert …` subcommand today** — the generic `sf api request rest` wrapper is the CLI surface for AHM alerts. If/when dedicated subcommands ship, prefer them and their `--help`.
> - `sf api request rest` is GA and bundled with the Salesforce CLI (no extra plugin required); it is the sole API surface used throughout this reference.
> - **API version.** Every endpoint below uses **`/services/data/v66.0/`**. For these resources the data API version is largely orthogonal to resource availability — v66.0 is the standardized floor here and `v68.0` also works on current orgs. Only raise the version if you need a field added in a later release; if any call unexpectedly returns `404`, retry at the org's current API version before assuming the resource is missing.
> - Reuse **Phase 0 (Discover Data Space)** from the main skill for the `dataspace` value used by the Data Cloud SQL and semantic queries below (default: `default`).

### Resolve the owner user ID

The list endpoint requires an `ownerId`. Resolve the current user (or another user by username):

```bash
# Current user (preferred — no user-supplied input)
USER_ID=$(sf org display user --target-org <org> --json \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["id"])')

# Another user, supplied out-of-band as a validated Salesforce User Id (15 or 18 chars).
# Prefer an Id over a username — it needs no query and can't inject.
USER_ID="005XXXXXXXXXXXXXXX"
[[ "$USER_ID" =~ ^[a-zA-Z0-9]{15,18}$ ]] || { echo "Not a valid User Id" >&2; exit 1; }
```

**Do not** build the owner query by interpolating a free-text username into `--query "… Username = '<value>'"`. That value crosses two hostile boundaries at once — the SOQL string literal (`x' OR IsActive=true LIMIT 1` subverts the predicate → resolves an arbitrary user's Id) and the surrounding double-quoted shell word (`$(…)`/backticks execute before `sf` runs). `agentforce-observe` reads production session data, so a username can be attacker-influenced, not just operator-typed.

If a username lookup is genuinely unavoidable, first reject anything with quoting/shell metacharacters, then build the SOQL in a `python3` snippet that reads the value from an environment variable and escapes the literal — never inline in a double-quoted `--query`:

```bash
UNAME='other@example.com'
# Reject any quote / backtick / $ / backslash / ; before the value is used.
printf '%s' "$UNAME" | LC_ALL=C grep -q "[\"'\`\$\\;]" && { echo "Reject: unsafe chars in username" >&2; exit 1; }
# UNAME is already validated above (no quotes/backslashes/shell metachars), so interpolate it directly.
SOQL=$(UNAME="$UNAME" python3 -c \
  'import os;print("SELECT Id FROM User WHERE Username = \x27%s\x27" % os.environ["UNAME"])')
USER_ID=$(sf data query --target-org <org> --json --query "$SOQL" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"]["records"][0]["Id"])')
```

---

## The endpoint: `tableau/dataAlerts`

AHM alerts are a special flavor of Salesforce data alerts — `dataAlertType: "agenthealthmonitoring"` — exposed under a dedicated REST resource:

```text
/services/data/v66.0/tableau/dataAlerts
```

They are **not** served from `/wave/dataAlerts` (CRM Analytics) or `/analytics/dataAlerts`. The "tableau" namespace here is Tableau Next / Data Cloud analytics, distinct from classic Wave — `/tableau/dataAlerts` does **not** require Wave / CRM Analytics.

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/services/data/v66.0/tableau/dataAlerts?ownerId={userId}` | List alerts for a user (requires `ownerId`) |
| POST   | `/services/data/v66.0/tableau/dataAlerts` | Create |
| PUT    | `/services/data/v66.0/tableau/dataAlerts/{alertId}` | Update (not yet available — see below) |
| DELETE | `/services/data/v66.0/tableau/dataAlerts/{alertId}` | Delete |
| GET    | `/services/data/v66.0/tableau/dataAlerts/{alertId}` | Not supported — 405 Method Not Allowed |

Single-alert GET is not supported — list all and filter client-side. Omitting `ownerId` on the list GET returns `400 MISSING_PARAM: Owner ID cannot be empty`. There is no "list all alerts across the org" shape; always scope to a user.

---

## List and describe alerts

```bash
sf api request rest "/services/data/v66.0/tableau/dataAlerts?ownerId=$USER_ID" -o <org> \
  | python3 -m json.tool
```

Example response (`totalSize: 1`):

```json
{
  "dataAlerts": [
    {
      "id": "3VRxx0000001xxxxAY",
      "alertName": "te1_AHM_High_AHM_Escalation_Rate_mtc::Service_Agent_Analytics_SDM_1f8_AHM_Above_0.1_AHM_All",
      "dataAlertType": "agenthealthmonitoring",
      "createdDate": "2026-05-01T23:01:02.000Z",
      "schedule": {"type": "everynminutes", "minuteLevelFrequency": 1},
      "thresholds": {
        "conditions": [{
          "leftOperand": {
            "type": "insights",
            "factKey": "FACT_KEY_TARGET_PERIOD_VALUE",
            "filterContext": [],
            "insightType": "popc",
            "metricId": "1HUxx000000xxxx4AE",
            "modelApiNameOrId": "2SMxx000000xxxx4AY",
            "timeContext": {"operator": "LastNHours", "values": ["1"]}
          },
          "operator": "greaterorequal",
          "rightOperand": {"type": "rawvalue", "dataType": "number", "value": "0.1"}
        }],
        "customLogicalOperation": "1"
      },
      "deliveryConfigurations": {
        "receivers": [
          {"type": "notification", "recipients": ["005xx000001xxxxAAC"]},
          {"type": "email", "recipients": ["005xx000001xxxxAAC"]}
        ]
      }
    }
  ],
  "totalSize": 1
}
```

Observations from a live response:

1. **`alertName` is an encoded form** — `_AHM_`-separated: `<freeText>_AHM_<severity>_AHM_<metricApiName>::<sdmApiName>_AHM_<operator>_<threshold>_AHM_<scope>`.
2. **`modelApiNameOrId` can be an ID** (e.g. `2SMxx…`), not always an API name.
3. **`filterContext: []`** even when the alert name indicates filters — this is a **known bug**. The real filters live in the **sub-metric** referenced by `metricId`.
4. **`schedule.minuteLevelFrequency: 1`** — fires every minute (aggressive; useful for test/demo).

### Retrieve the sub-metric to see the actual filters

```bash
METRIC_ID="1HUxx000000xxxx4AE"
MODEL="Service_Agent_Analytics_SDM"   # or the ID from modelApiNameOrId
sf api request rest \
  "/services/data/v66.0/ssot/semantic/models/${MODEL}/sub-metrics/${METRIC_ID}" -o <org> \
  | python3 -m json.tool
```

HTTP 200 → it's a filtered sub-metric; `filters[]` holds the real agent-name / agent-type conditions.

---

## Prerequisite for creating alerts: confirm the three alertable SDMs

> **Scope rule.** AHM data alerts target **exactly three** semantic data models. **Ignore every other SDM** returned by the endpoint — including `Agent_Health_Monitoring_SDM`, dataset-specific models, or custom models. If the metric you want isn't in one of the three below, the answer is "not supported," not "try another SDM."

1. **Agentforce Analytics Foundations** — base model. API name `sfm_Agentforce_Analytics_Foundations` (stable). Exposes only `_clc`, no `_mtc`.
2. **Employee Agent Analytics SDM** — match by **label** `Employee Agent Analytics SDM` or **`app` = `Employee_Agent_Analytics`**.
3. **Service Agent Analytics SDM** — match by **label** `Service Agent Analytics SDM` or **`app` = `Service_Agent_Analytics`**.

> **Never hard-code the `_1f8` (or any other) `apiName` suffix.** It's a content-hash / provisioning token that changes when the app template is re-provisioned or moved to another org. Always discover the live `apiName` by listing models and matching on the stable fields (`label`, `app`), then read `apiName` back out.

### List all semantic models

```bash
sf api request rest "/services/data/v66.0/ssot/semantic/models" -o <org> \
  | python3 -m json.tool
```

Example `items[]` entry:

```json
{
  "apiName": "Service_Agent_Analytics_SDM_1f8",
  "app": "Service_Agent_Analytics",
  "label": "Service Agent Analytics SDM",
  "id": "2SMxx000000xxxx4AY",
  "dataspace": "default",
  "baseModels": [
    {"apiName": "sfm_Agentforce_Analytics_Foundations", "label": "Agentforce Analytics Foundations"}
  ]
}
```

Key fields: `label` (stable match), `apiName` (goes into `modelApiNameOrId`, has the suffix), `app`/`sourceCreationName` (stable app identifiers), `id` (SDM record ID — needed for the semantic-engine gateway).

### Provisioning check — the three only, ignore everything else

```bash
export ORG=<org>
sf api request rest "/services/data/v66.0/ssot/semantic/models" -o "$ORG" | python3 <<'PY'
import json, sys
models = json.load(sys.stdin).get("items", [])

# Allowlist: exactly the three AHM-alertable SDMs. Match by stable fields only.
IN_SCOPE = [
    ("Agentforce Analytics Foundations", None),
    ("Employee Agent Analytics SDM",     "Employee_Agent_Analytics"),
    ("Service Agent Analytics SDM",      "Service_Agent_Analytics"),
]

def match(m, label, app):
    return m.get("label") == label or (app and m.get("app") == app)

print(f"{'SDM (in scope)':40} {'apiName':45} {'id':25} status")
print("-" * 120)
resolved_ids = set()
for label, app in IN_SCOPE:
    hits = [m for m in models if match(m, label, app)]
    if not hits:
        print(f"{label:40} {'(not found)':45} {'':25} Not provisioned — cannot alert on this SDM")
        continue
    m = hits[0]
    resolved_ids.add(m.get("id"))
    print(f"{label:40} {m.get('apiName','?'):45} {str(m.get('id','?')):25} provisioned")

ignored = [m for m in models if m.get("id") not in resolved_ids]
print(f"\nIgnored — out of scope ({len(ignored)} model(s)). Do NOT alert on these:")
for m in ignored:
    print(f"  • {m.get('label','?')} (apiName={m.get('apiName','?')})")
if not ignored:
    print("  (none)")
PY
```

Interpreting the output:
- All three provisioned → proceed to create alerts; use the `apiName` values as-is for `modelApiNameOrId`.
- Any Not provisioned → that SDM's app template is not provisioned on this org. Alerts cannot be created against it until the template is deployed (a provisioning task, not a CLI workaround).
- Anything "Ignored" → acknowledge and move on. **Do not** substitute an ignored SDM for a missing in-scope one.

Troubleshooting:
- **Only Foundations shows up** — the Employee/Service app templates haven't been provisioned; they must be deployed via the Analytics app template flow first.
- **`FUNCTIONALITY_NOT_ENABLED` on `/ssot/semantic/models`** — Data Cloud / SSOT is not provisioned; none of the alertable SDMs can exist.
- **API name doesn't match `modelApiNameOrId` in an existing alert** — the alert was created against an older provisioning hash. Delete and recreate against the current `apiName`.

---

## Enumerate `_mtc` metrics and screen for time-grain fit

The alertable atoms inside each SDM are **semantic metrics** whose API names end in `_mtc`. These differ from the `_clc` calculated measurements:

| Endpoint | Object | Suffix | What it is |
|---|---|---|---|
| `…/calculated-measurements` | Calculated measurement | `_clc` | Low-level aggregation at the SDM layer (raw ingredient). |
| `…/metrics` | Semantic metric | `_mtc` | Wraps a `_clc` with time dimension, grains, insight settings. **This is what data alerts reference.** |
| `…/sub-metrics` | Sub-metric | id `1HU…` | A filtered instantiation of a `_mtc`. Most real alerts' `metricId` is a sub-metric, not the bare `_mtc`. |

### List all `_mtc` across the three SDMs

```bash
export ORG=<org>
python3 <<'PY'
import json, subprocess

def rest(path):
    out = subprocess.check_output(["sf","api","request","rest",path,"-o",__import__("os").environ["ORG"]])
    return json.loads(out)

models = rest("/services/data/v66.0/ssot/semantic/models").get("items", [])
IN_SCOPE_APPS = {
    "Agentforce Analytics Foundations": None,
    "Employee Agent Analytics SDM":     "Employee_Agent_Analytics",
    "Service Agent Analytics SDM":      "Service_Agent_Analytics",
}
resolved = {}
for m in models:
    for label, app in IN_SCOPE_APPS.items():
        if m.get("label") == label or (app and m.get("app") == app):
            resolved[label] = m["apiName"]
            break

for label, api in resolved.items():
    metrics = rest(f"/services/data/v66.0/ssot/semantic/models/{api}/metrics").get("metrics", [])
    mtc = [m for m in metrics if m.get("apiName","").endswith("_mtc")]
    print(f"\n=== {label} ({api})  —  {len(mtc)} _mtc metric(s) ===")
    for m in mtc:
        grains = ",".join(m.get("timeGrains", [])) or "(no timeGrains)"
        print(f"  {m['apiName']:40} | {m.get('label',''):30} | id={m.get('id','')} | grains=[{grains}]")
    if not mtc:
        print("  (none — e.g. Foundations exposes only _clc)")
PY
```

On a typical org, Foundations exposes **0** `_mtc`; Service Analytics SDM exposes ~14 (`Escalation_Rate_mtc`, `Deflection_Rate_mtc`, `Abandonment_Rate_mtc`, `Engagement_Rate_mtc`, `Agent_Health_Score_mtc`, `Total_Sessions_mtc`, …); Employee Analytics SDM exposes ~9 (`Stickiness_Rate_mtc`, `Total_Unique_Users_mtc`, `Weekly_Active_Users_mtc`, …). All declare `timeGrains = [Day, Week, Month, Quarter, Year]` — none declare Hour/Minute, but the `dataAlerts` API doesn't enforce this (the alert's `timeContext.operator` is independent).

Pull the `id` of the chosen `_mtc` — it goes into `thresholds.conditions[].leftOperand.metricId` when creating an alert.

### Screening: does the metric make sense at a short window?

The SDM doesn't block nonsense; apply judgement:

| Metric shape | Smallest useful window | Short-window (≤ 1h) alert? |
|---|---|---|
| **Ratios / rates** — Engagement, Deflection, Abandonment, Escalation, Stickiness | 15 min – 1 h | Yes — self-normalizing. Add a minimum-volume guard. |
| **Averages / times** — Avg Time to Deflection/Escalation/Execution, Avg Quality Score | ≥ 1 h | Borderline at 1–4h; daily is fine. Not at 15 min. |
| **Cumulative totals** — Total/Deflected/Escalated/Abandoned/Engaged Sessions, Total Actions | ≥ 1 h, typically ≥ 1 day | No — noisy at short windows — alert on the corresponding **rate** instead. |
| **Cardinality counts** — Unique Users, Weekly Active Users, Total Employee Agents | ≥ 1 day | No — smallest sensible window Day (DAU) / Week (WAU). |
| **Composite scores** — Agent Health Score | default ≥ 1 day | Depends on inputs; default no. |

> **Minimum-volume guard.** Even for ratios, check the denominator: a 100% error rate on 1 session in 15 min is noise. The API has no built-in guard — pre-filter via a sub-metric requiring N > threshold sessions, or combine a rate threshold AND an absolute-count threshold in `thresholds.conditions[]`.

Use short-window rate metrics with `schedule.minuteLevelFrequency ≤ 60` and `timeContext.operator = LastNHours|LastNMinutes`; use daily+ metrics only with `minuteLevelFrequency ≥ 1440` and `LastNDays`/`LastNWeeks`.

---

## List the agents available for alert filters

The UI Create-Alert modal scopes an alert to an **Agent Name** or **Agent Type**. Those values come from **live session-tracing data (Data Cloud DLO)**, not from agent metadata.

> **For AHM alerts, use the DLO query (ground truth) below.** If a name appears in `BotDefinition` but has never run a session, the filter selects zero sessions and the alert never fires. A name in the DLO without a `BotDefinition` (demo/external agents) is still alertable — the filter matches strings, not IDs.
>
> **Cross-link:** the DLO object below, `ssot__AiAgentSessionParticipant__dlm`, is the same DMO documented in [`stdm-schema.md`](stdm-schema.md). Note the AHM filter uses `ssot__AiAgentApiName__c` here, which is **not** the same as the `GenAiPlannerDefinition` `MasterLabel`/`DeveloperName` the main skill resolves for STDM `findSessions` — grab the filter value from this query, don't reconstruct it.

### DLO query (ground truth)

Write the SQL body to a private temp file (see the `mktemp` idiom above) to avoid shell-escaping, then POST it:

```bash
body=$(mktemp) && chmod 600 "$body"
trap 'rm -f "$body"' EXIT
cat > "$body" <<'JSON'
{
  "sql": "SELECT ssot__AiAgentApiName__c AS agent_name, ssot__AiAgentType__c AS agent_type, COUNT(*) AS participant_rows FROM ssot__AiAgentSessionParticipant__dlm WHERE ssot__AiAgentSessionParticipantRole__c != 'USER' GROUP BY ssot__AiAgentApiName__c, ssot__AiAgentType__c ORDER BY agent_name",
  "rowLimit": 500,
  "adaptiveTimeout": 1
}
JSON

sf api request rest "/services/data/v66.0/ssot/query-sql?dataspace=default" \
  -X POST -H "Content-Type: application/json" -b "@$body" -o <org> \
  | python3 -m json.tool
```

The `ssot__AiAgentSessionParticipantRole__c != 'USER'` clause filters out the human side of the conversation. `GROUP BY` already yields one row per distinct `(agent_name, agent_type)` pair — no `DISTINCT` needed. In the `data` array: column 0 = `agent_name` (→ `AI_Agent_Api_Name` filter values), column 1 = `agent_type`, column 2 = `participant_rows` (volume sanity check — an agent with a handful of rows is too sparse for a 15-min alert).

### Metadata cross-reference (fallback)

```bash
sf data query --target-org <org> \
  --query "SELECT Id, DeveloperName, MasterLabel, AgentType FROM BotDefinition ORDER BY DeveloperName"
```

Not required for alerting. `AiAgent` sObject is often not queryable via REST — don't rely on it.

### Next-Gen Authoring Bundles API (what agents are defined)

Works even where `BotDefinition`/`AiAgent` sObjects are not queryable (common on demo orgs):

```bash
sf api request rest "/services/data/v66.0/nextgen-authoring/bundles" -o <org> | python3 -m json.tool
# names only:
sf api request rest "/services/data/v66.0/nextgen-authoring/bundles" -o <org> \
  | python3 -c 'import sys,json; [print(b.get("apiName","?")) for b in json.load(sys.stdin).get("bundles", [])]'
```

`apiName` is the agent's developer name (the value usable as an alert filter); `isLegacy: false` = new Next-Gen agent. Requires `NextGenAuthoring.orgHasNextGenAgentAuthoringEnabled` + `…userCanAccessNextGenAgentAuthoring`, else 403 (the `.get("bundles", [])` above then prints nothing rather than raising).

**Use the DLO query (ground truth) for filter values.** The metadata cross-reference and Bundles API are for discovery/cross-ref only. An agent listed there but absent from the DLO has never run a session — alerting on it matches zero rows until sessions arrive.

Troubleshooting:
- **`query-sql` 400 / FUNCTIONALITY_NOT_ENABLED** — SSOT/Data Cloud not enabled; no agent-tracing data exists and alerts can't fire.
- **Zero rows** — no sessions have landed. Confirm session-tracing is on and data has flowed.
- **UI dropdown shows values not in the DLO query** — check the `dataspace`; change `?dataspace=` if the alert is scoped to a non-`default` space.

---

## Create an alert

`POST /services/data/v66.0/tableau/dataAlerts`. Inputs come from the sections above: `modelApiNameOrId` (SDM `apiName`/`id`), `metricId` (`_mtc` `id`), and `filterContext` (agent name/type from the DLO query above).

### POST field names ≠ GET field names

The POST input representation uses **different field names and casing** from the GET response:

| POST (input) | GET (output) | Notes |
|---|---|---|
| `utterance` | `alertName` | POST field is `utterance`; response returns `alertName` |
| `type: "Metric"` (leftOperand) | `type: "insights"` | PascalCase in, lowercase out |
| `type: "RawValue"` (rightOperand) | `type: "rawvalue"` | same pattern |
| `type: "EveryNMinutes"` (schedule) | `type: "everynminutes"` | same |
| `type: "Notification"` / `"Email"` | `type: "notification"` / `"email"` | same |
| `operator: "GreaterOrEqual"` | `operator: "greaterorequal"` | same |
| `insightType: "Popc"` | `insightType: "popc"` | same |

**Rule of thumb:** all `type` discriminators and enum values in the POST body use **PascalCase**; the GET response lowercases everything. Copying a GET response and POSTing it back fails with `JSON_PARSER_ERROR`.

### filterContext field-name format

Filter field names use **dot notation**: `{tableApiName}.{fieldApiName}`. The metric's `additionalDimensions` lists the available dimensions as `tableFieldReference` objects — concatenate `tableApiName` + `.` + `fieldApiName`:

```text
tableApiName: "Agent_API_Name_lv"
fieldApiName: "AI_Agent_Session_Participant2_AI_Agent_Api_Name"
→ filterContext fieldName: "Agent_API_Name_lv.AI_Agent_Session_Participant2_AI_Agent_Api_Name"
```

Using just the `fieldApiName` fails with `INTERNAL_ERROR: Validation Failed: Invalid calculated Field`.

### Sub-metric auto-creation

When you POST with a non-empty `filterContext`, the backend **auto-creates a sub-metric** (ID prefix `1HU…`) from the bare `_mtc` id plus your filters. The response's `metricId` is the new sub-metric id, not the `_mtc` id you sent. You don't create sub-metrics manually. (The response's `filterContext` comes back `[]` — the known bug; fetch the sub-metric to see the real filters.)

### Threshold values are raw ratios, not display percentages

Rate metrics are a **0–1 ratio** (the UI multiplies by 100 for display; the alert threshold operates on the raw value):

| You want to alert at | Threshold `value` |
|---|---|
| 1% | `"0.01"` |
| 5% | `"0.05"` |
| 50% | `"0.5"` |
| 100% | `"1"` |

> `value: "1"` means ≥ 100%, not ≥ 1%. An alert with `"1"` on a rate metric is either a test alert designed to always fire, or a misconfiguration.

### Full POST schema

```json
{
  "utterance": "<alert name — encoded or freeform string>",
  "dataAlertType": "agenthealthmonitoring",
  "schedule": { "type": "EveryNMinutes", "minuteLevelFrequency": <integer minutes> },
  "content": { "type": "Metric", "modelApiNameOrId": ["<SDM ID or apiName>"] },
  "thresholds": {
    "conditions": [
      {
        "leftOperand": {
          "type": "Metric",
          "modelApiNameOrId": "<SDM ID or apiName>",
          "metricId": "<_mtc id>",
          "insightType": "Popc",
          "factKey": "FACT_KEY_TARGET_PERIOD_VALUE",
          "params": {},
          "filterContext": [
            { "fieldName": "<table.field dot notation>", "operator": "Equals", "values": ["<filter value>"] }
          ],
          "timeContext": { "operator": "LastNHours", "values": ["<hours>"] }
        },
        "operator": "GreaterOrEqual",
        "rightOperand": { "type": "RawValue", "dataType": "Number", "value": "<threshold as string>" }
      }
    ],
    "customLogicalOperation": "1"
  },
  "deliveryConfigurations": {
    "receivers": [
      { "type": "Notification", "recipients": ["<userId>"] },
      { "type": "Email", "recipients": ["<userId>"] }
    ]
  }
}
```

### Example: Escalation Rate ≥ 1% for agent `te1`, checked every 15 minutes

Build the body in a private temp file (see the `mktemp` idiom above), then POST it. The literal-value heredoc below shows the exact shape (verified against a real org) with **constant** example values — safe to paste as-is because nothing is substituted:

```bash
body=$(mktemp) && chmod 600 "$body"
trap 'rm -f "$body"' EXIT
cat > "$body" <<'JSON'
{
  "utterance": "te1_AHM_High_AHM_Escalation_Rate_mtc::Service_Agent_Analytics_SDM_1f8_AHM_Above_0.01_AHM_te1",
  "dataAlertType": "agenthealthmonitoring",
  "schedule": { "type": "EveryNMinutes", "minuteLevelFrequency": 15 },
  "content": { "type": "Metric", "modelApiNameOrId": ["2SMSG000000a6TV4AY"] },
  "thresholds": {
    "conditions": [
      {
        "leftOperand": {
          "type": "Metric",
          "modelApiNameOrId": "2SMSG000000a6TV4AY",
          "metricId": "1DOSG0000051KAm4AM",
          "insightType": "Popc",
          "factKey": "FACT_KEY_TARGET_PERIOD_VALUE",
          "params": {},
          "filterContext": [
            { "fieldName": "Agent_API_Name_lv.AI_Agent_Session_Participant2_AI_Agent_Api_Name", "operator": "Equals", "values": ["te1"] }
          ],
          "timeContext": { "operator": "LastNHours", "values": ["1"] }
        },
        "operator": "GreaterOrEqual",
        "rightOperand": { "type": "RawValue", "dataType": "Number", "value": "0.01" }
      }
    ],
    "customLogicalOperation": "1"
  },
  "deliveryConfigurations": {
    "receivers": [
      { "type": "Notification", "recipients": ["<USER_ID>"] },
      { "type": "Email", "recipients": ["<USER_ID>"] }
    ]
  }
}
JSON

sf api request rest "/services/data/v66.0/tableau/dataAlerts" \
  -X POST -H "Content-Type: application/json" -b "@$body" -o <org> \
  | python3 -m json.tool
```

**When the agent name, `utterance`, filter value, threshold, or recipient come from data — not typed by hand — do not string-substitute them into the heredoc.** An agent name sourced from live DLO/session data can contain a `"` that breaks out of the JSON string and injects sibling fields (e.g. an attacker-controlled `Email` receiver that exfiltrates notifications, or a corrupted threshold that silently disables the alert). Reject values containing `"`/`\`, then let a JSON-aware builder encode everything — the body is byte-safe regardless of what the values contain:

```bash
# AGENT_NAME / UTTERANCE / THRESHOLD (raw ratio) / MODEL_ID / METRIC_ID / USER_ID come from earlier discovery.
case "$AGENT_NAME$UTTERANCE" in *[\"\\]*) echo "Reject: quote/backslash in name or utterance" >&2; exit 1;; esac
body=$(mktemp) && chmod 600 "$body"
trap 'rm -f "$body"' EXIT
AGENT_NAME="$AGENT_NAME" UTTERANCE="$UTTERANCE" THRESHOLD="$THRESHOLD" \
MODEL_ID="$MODEL_ID" METRIC_ID="$METRIC_ID" USER_ID="$USER_ID" python3 - > "$body" <<'PY'
import os, sys, json
e = os.environ
json.dump({
  "utterance": e["UTTERANCE"],
  "dataAlertType": "agenthealthmonitoring",
  "schedule": {"type": "EveryNMinutes", "minuteLevelFrequency": 15},
  "content": {"type": "Metric", "modelApiNameOrId": [e["MODEL_ID"]]},
  "thresholds": {"conditions": [{
    "leftOperand": {"type": "Metric", "modelApiNameOrId": e["MODEL_ID"], "metricId": e["METRIC_ID"],
      "insightType": "Popc", "factKey": "FACT_KEY_TARGET_PERIOD_VALUE", "params": {},
      "filterContext": [{"fieldName": "Agent_API_Name_lv.AI_Agent_Session_Participant2_AI_Agent_Api_Name",
        "operator": "Equals", "values": [e["AGENT_NAME"]]}],
      "timeContext": {"operator": "LastNHours", "values": ["1"]}},
    "operator": "GreaterOrEqual",
    "rightOperand": {"type": "RawValue", "dataType": "Number", "value": e["THRESHOLD"]}}],
    "customLogicalOperation": "1"},
  "deliveryConfigurations": {"receivers": [
    {"type": "Notification", "recipients": [e["USER_ID"]]},
    {"type": "Email", "recipients": [e["USER_ID"]]}]},
}, sys.stdout)
PY

sf api request rest "/services/data/v66.0/tableau/dataAlerts" \
  -X POST -H "Content-Type: application/json" -b "@$body" -o <org> \
  | python3 -m json.tool
```

The response (HTTP 200) returns `id` (the alert id, prefix `3VR…`), and a `metricId` with prefix `1HU…` — the auto-created sub-metric, not the `1DO…` bare metric you sent. Response `filterContext` is `[]` (known bug); confirm the real filter via the sub-metric fetch shown earlier. All enum values in the response are lowercase.

### Example: unfiltered alert (all agents)

Same body, but `"filterContext": []` and (typically) `minuteLevelFrequency: 60` — no sub-metric is created; the alert references the bare `_mtc` id directly.

### Available enum values

- **Schedule types:** `"EveryNMinutes"` (+`minuteLevelFrequency`), `"Daily"` (+`hoursOfDay`), `"Weekly"` (+`hoursOfDay`,`daysOfWeek`).
- **Condition operators:** `"Equals"`, `"NotEqual"`, `"GreaterThan"`, `"GreaterOrEqual"`, `"LessThan"`, `"LessOrEqual"`.
- **Value types:** `"Metric"` (leftOperand); `"RawValue"` (rightOperand) with `dataType` `"Number"`/`"Text"`/`"Percent"`.
- **Receiver types:** `"Notification"` / `"Email"` (recipients = user IDs); `"Slack"` (recipients = Slack channel IDs).
- **Insight types:** `"Popc"` (period-over-period — used by AHM), `"RiskyMonopoly"`, `"Unspecified"`.
- **Filter operators:** `"Equals"`, `"DoesNotEquals"`, `"LessThan"`, `"GreaterThan"`, `"LessOrEqual"`, `"GreaterOrEqual"`, `"Between"`, `"IsNull"`, `"IsNotNull"`, `"Contains"`, `"DoesNotContain"`, `"StartsWith"`, `"EndsWith"`, `"In"`, `"NotIn"`.
- **Time-context operators:** `"LastNHours"`, `"LastNDays"`, `"LastNWeeks"`, `"LastNMonths"`, `"LastNQuarters"`, `"LastNYears"`, `"LastNMinutes"`.

### Constructing the `utterance` (alert name)

Conventional encoded format the AHM UI parses (the backend accepts arbitrary strings):

```text
{freeText}_AHM_{severity}_AHM_{metricApiName}::{sdmApiName}_AHM_{operator}_{threshold}_AHM_{scope}
```

`severity` = `High`/`Medium`/`Low`; `operator` = `Above`/`Below`; `scope` = `All` (no filter) or the filter value. Using this format lets the AHM UI display the alert correctly.

### Troubleshooting

- **`JSON_PARSER_ERROR: Unrecognized field`** — using a GET-response field name in the POST. Common: `alertName` → use `utterance`; `intervalInMinutes` → `minuteLevelFrequency`.
- **`JSON_PARSER_ERROR: Could not resolve type id`** — wrong casing on a `type` discriminator. Use PascalCase (`"Metric"`, `"RawValue"`, `"EveryNMinutes"`, …).
- **`INTERNAL_ERROR: Validation Failed: Invalid calculated Field`** — filter `fieldName` missing the table prefix; use dot notation.
- **`400` with no clear message** — `content.modelApiNameOrId` must be an **array** (`["2SM…"]`), not a string.
- **Alert created but never fires** — the agent name in `filterContext.values` must exactly match a DLO value (from the DLO query in "List the agents available for alert filters"). If the agent has never had a session, there's no data to alert on.

---

## Update an alert

The PUT API (`PUT /services/data/v66.0/tableau/dataAlerts/{alertId}`) is **not yet available** (expected later 2026). Until then, **delete** the existing alert and **create** a new one with the updated configuration.

---

## Delete an alert

```bash
ALERT_ID="3VRSG0000001kX34AI"   # from the list or the create response
sf api request rest "/services/data/v66.0/tableau/dataAlerts/$ALERT_ID" -X DELETE -o <org> --include
```

Returns **HTTP 204** (No Content) on success — no response body. Use `--include` to see the status line.

---

## Trigger history — inspect triggered notifications

When an alert's condition is met it generates a **system notification** and optionally an **email** (per `deliveryConfigurations.receivers`).

### Check notification counts via CLI (org-global signal only)

```bash
sf api request rest "/services/data/v66.0/connect/notifications/status" -o <org> | python3 -m json.tool
```

Returns `unreadCount` and `unseenCount`. **These are org-global counts across *all* notification types — not per-alert, and not AHM-specific.** A non-zero count means *some* notification was generated (it could be any alert or any other notification), so treat it only as a coarse "something fired" signal, never as confirmation that *this* alert fired. For per-alert trigger history, use the UI Incidents tab below.

### Other verification paths

- **UI (per-alert trigger history)** — `/lightning/n/standard-AgentforceStudio?c__nav=alerts` → **Incidents** tab is the only surface with the full, per-alert notification list and details. Route the user here whenever they need to confirm a *specific* alert fired or see its history.
- **Email** — if `deliveryConfigurations` includes `"type": "Email"`, the owner receives an email when it fires.
- **Metric value** — confirm the underlying metric actually crosses the threshold (see next section).

### Troubleshooting alerts that don't fire

`unreadCount: 0` is a weak signal (it means no *unread* notifications org-wide — already-read ones don't count). Confirm in the Incidents tab that the specific alert has no history, then check:
1. **Does the SDM return data?** If the semantic gateway (below) returns null/0, the alert evaluation also returns null and the condition is never met.
2. **Is the schedule running?** Alerts evaluate on their `minuteLevelFrequency`; a freshly created alert may take a few cycles.
3. **Does the threshold make sense?** A 10% rate with threshold `>= 0.5` (50%) never fires — remember the raw-0–1-ratio scale.

---

## Verify metric value via Semantic Engine Gateway (condensed)

Use this to confirm a metric actually crosses the threshold before concluding an alert is broken. The gateway queries any `_clc` calculated measurement with time grouping / filters / aggregation.

**Endpoint:** `POST /services/data/v66.0/semantic-engine/gateway`. Inputs: SDM **record ID** (the `id`, not `apiName`), the `_clc` name (from the metric's `measurementReference.calculatedFieldApiName`), the time dimension (`AI_Agent_Session.Start_Timestamp` for session-level rates), and an ISO date range. Rate values come back as **raw 0–1 ratios**, same scale as alert thresholds.

### Single aggregate value (e.g. overall Escalation Rate for the last 24h)

```bash
body=$(mktemp) && chmod 600 "$body"
trap 'rm -f "$body"' EXIT
cat > "$body" <<'JSON'
{
  "structuredSemanticQuery": {
    "fields": [
      {
        "expression": { "semanticField": { "name": "Escalation_Rate_clc" } },
        "alias": "Escalation_Rate",
        "rowGrouping": false,
        "semanticAggregationMethod": "SEMANTIC_AGGREGATION_METHOD_USER_AGG"
      }
    ],
    "topNFilter": { "rowsNumber": 1, "sortOrders": [] },
    "options": { "limitOptions": { "limit": 2 }, "sortOrders": [], "grandTotal": false },
    "semantic_context": { "currency": { "id": "" } },
    "flattenFilter": {
      "filters": [
        { "fieldName": "AI_Agent_Session.Start_Timestamp", "operator": "Between", "value": "2026-05-02T00:00:00.000Z|2026-05-03T00:00:00.000Z" }
      ],
      "filterLogic": "1"
    }
  },
  "semanticModelId": "2SMSG000000a6TV4AY"
}
JSON

sf api request rest "/services/data/v66.0/semantic-engine/gateway" \
  -X POST -H "Content-Type: application/json" -b "@$body" -o <org> \
  | python3 -m json.tool
```

### Time series (per-day) and agent filter

For a per-day series, add a first field with `"rowGrouping": true` and a `DATETRUNC('day', [AI_Agent_Session].[Start_Timestamp])` calculated field (alias e.g. `Day`), set `topNFilter.rowsNumber` = N, `options.limitOptions.limit` = N+1, and `grandTotal: true`. To scope to an agent, add a second `flattenFilter.filters` entry `{ "fieldName": "AI_Agent_Session_Participant.AI_Agent_Api_Name", "operator": "In", "value": "te1" }` (comma-separated for multiple) and set `"filterLogic": "1 AND 2"`.

Response rows carry `is_data_row__sl` (`true` = data row, `false` = grand total) and `grouping_1__sl` (`0` = detail, `1` = total); the `values` array is indexed by each field's `placeInOrder`.

### Discover available `_clc` measurements

```bash
SDM_API_NAME="Service_Agent_Analytics_SDM_1f8"
sf api request rest "/services/data/v66.0/ssot/semantic/models/${SDM_API_NAME}/calculated-measurements" -o <org> \
  | python3 -c 'import sys,json;[print(m["apiName"],"|",m.get("label",""),"|",m.get("dataType","")) for m in json.load(sys.stdin).get("items",[])]'
```

Common Service SDM measures: `Escalation_Rate_clc`, `Deflection_Rate_clc`, `Engagement_Rate_clc`, `Abandonment_Rate_clc`, `Error_Rate_clc`, `Unique_Sessions_clc`, `Escalated_Sessions_clc`, `Average_Session_Duration_clc`.

Troubleshooting:
- **`null` values** — verify data exists in the DLO (`SELECT COUNT(*) FROM ssot__AiAgentSession__dlm` via `query-sql`). DLO has rows but gateway returns null → the SDM-to-DLO mapping is broken (provisioning issue).
- **`USER_ILLEGAL_ARGUMENT_RESOLVE_ENTITY_ERROR: Failed to resolve semantic field`** — wrong `_clc` name; list measurements with the discovery command.
- **`404 Not Found`** — confirm the path is `/services/data/v66.0/semantic-engine/gateway`; if it still 404s, retry at the org's current API version (the resource may be exposed at a different version on that org).

---

## Global troubleshooting

| Error | Cause / fix |
|---|---|
| `400 MISSING_PARAM: Owner ID cannot be empty` | The list GET requires `?ownerId={userId}`. |
| `405 Method Not Allowed` on `/tableau/dataAlerts/{id}` | Single-alert GET unsupported — list and filter by `id` client-side. |
| `401 Bad_OAuth_Token` | Token expired — `sf api request rest` refreshes automatically on the next call. |
| `404` on `/wave/dataAlerts` or `/analytics/dataAlerts` | Wrong namespace — AHM alerts live under `/tableau/dataAlerts`. |
| `FUNCTIONALITY_NOT_ENABLED: [Wave]` | Unrelated — `/tableau/dataAlerts` does not require Wave / CRM Analytics. |
