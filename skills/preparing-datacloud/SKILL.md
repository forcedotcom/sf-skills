---
name: preparing-datacloud
description: "Salesforce Data Cloud Prepare phase. Use this skill when the user creates or manages Data Cloud data streams, DLOs, transforms, or Document AI configurations. TRIGGER when: user creates or manages Data Cloud data streams, DLOs, transforms, or Document AI configurations, or asks about ingestion into Data Cloud. DO NOT TRIGGER when: the task is connection setup only (use connecting-datacloud), DMOs and identity resolution (use harmonizing-datacloud), or query/search work (use retrieving-datacloud)."
license: MIT
compatibility: "Requires an external community sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0"
---

# preparing-datacloud: Data Cloud Prepare Phase

Use this skill when the user needs **ingestion and lake preparation work**: data streams, Data Lake Objects (DLOs), transforms, Document AI, unstructured ingestion, or the handoff from connector setup into a live stream.

## When This Skill Owns the Task

Use `preparing-datacloud` when the work involves:
- `sf data360 data-stream *`
- `sf data360 dlo *`
- `sf data360 transform *`
- `sf data360 docai *`
- choosing how data should enter Data Cloud
- rerunning or rescanning ingestion after a source update
- preparing Ingestion API-backed streams after connector setup is complete

Delegate elsewhere when the user is:
- still creating/testing source connections → [connecting-datacloud](../connecting-datacloud/SKILL.md)
- mapping to DMOs or designing IR/data graphs → [harmonizing-datacloud](../harmonizing-datacloud/SKILL.md)
- querying ingested data → [retrieving-datacloud](../retrieving-datacloud/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- source connection name
- source object / dataset / document source
- desired stream type
- DLO naming expectations
- whether the user is creating, updating, running, or deleting a stream
- whether the source is CRM, a database connector, an unstructured file source, or an Ingestion API feed

---

## Core Operating Rules

- Verify the external plugin runtime before running Data Cloud commands.
- Run the shared readiness classifier before mutating ingestion assets: `node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase prepare --json`.
- Prefer inspecting existing streams and DLOs before creating new ingestion assets.
- Suppress linked-plugin warning noise with `2>/dev/null` for normal usage.
- Treat DLO naming and field naming as Data Cloud-specific, not CRM-native.
- Confirm whether each dataset should be treated as `Profile`, `Engagement`, or `Other` before creating the stream.
- Distinguish stream-level refresh from connection-level reruns when working with unstructured sources.
- Use UI setup intentionally when initial stream or unstructured asset creation is platform-gated.
- Hand off to Harmonize only after ingestion assets are clearly healthy.

---

## Recommended Workflow

### 1. Classify readiness for prepare work
```bash
node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase prepare --json
```

### 2. Inspect existing ingestion assets
```bash
sf data360 data-stream list -o <org> 2>/dev/null
sf data360 dlo list -o <org> 2>/dev/null
```

### 3. Confirm the stream category before creation
Use these rules when suggesting categories:

| Category | Use for | Typical requirement |
|---|---|---|
| `Profile` | person/entity records | primary key |
| `Engagement` | time-based events or interactions | primary key + event time field |
| `Other` | reference/configuration/supporting datasets | primary key |

When the source is ambiguous, ask the user explicitly whether the dataset should be treated as `Profile`, `Engagement`, or `Other`.

### 4. Create or inspect streams intentionally
```bash
sf data360 data-stream get -o <org> --name <stream> 2>/dev/null
sf data360 data-stream create-from-object -o <org> --object Contact --connection SalesforceDotCom_Home 2>/dev/null
sf data360 data-stream create -o <org> -f stream.json 2>/dev/null
sf data360 data-stream run -o <org> --name <stream> 2>/dev/null
```

### 5. Check DLO shape
```bash
sf data360 dlo get -o <org> --name Contact_Home__dll 2>/dev/null
```

### 6. Choose the right refresh mechanism
Use the smaller refresh scope that matches the user goal:

```bash
sf data360 data-stream run -o <org> --name <stream> 2>/dev/null
sf data360 connection run-existing -o <org> --name <connection-id> 2>/dev/null
```

- `data-stream run` is the closest match to a stream-level refresh or re-scan.
- `connection run-existing` runs at the connection level and can be useful for some connector workflows, but it is not a reliable replacement for stream refresh on unstructured sources.
- For unstructured document connectors, prefer `data-stream run` when the goal is to re-scan newly added or changed files.

### 7. Handle unstructured sources deliberately
For SharePoint-style document ingestion, a minimal unstructured DLO payload can look like:

```json
{
  "name": "my_udlo",
  "label": "My UDLO",
  "category": "Directory_Table",
  "dataSource": {
    "sourceType": "SF_DRIVE",
    "directoryAndFilesDetails": [
      {
        "dirName": "SPUnstructuredDocument/<CONNECTION_ID>/<SITE_ID>",
        "fileName": "*"
      }
    ],
    "sourceConfig": {
      "reservedPrefix": "$dcf_content$"
    }
  }
}
```

Use the UI for the first-time unstructured setup when the user needs the richer end-to-end pipeline. The UI path can seed additional document metadata fields and downstream assets that a bare CLI DLO create flow may not provision automatically.

### 8. Use the local Ingestion API example for send-data workflows
For external systems pushing records into Data Cloud:

1. create the connector in [connecting-datacloud](../connecting-datacloud/SKILL.md)
2. upload the schema with `sf data360 connection schema-upsert`
3. create the stream in the UI when required
4. send records with the local example in `examples/ingestion-api/`

```bash
cd examples/ingestion-api
cp .env.example .env
python3 send-data.py
```

Key details:
- auth is a staged flow: JWT → Salesforce token → Data Cloud token
- the ingestion endpoint uses the tenant URL, not the Salesforce instance URL
- `202` means the payload was accepted for processing, not that records are queryable immediately
- validation failures often surface in the Problem Records DLO family

### 9. Only then move into harmonization
Once the stream and DLO are healthy, hand off to [harmonizing-datacloud](../harmonizing-datacloud/SKILL.md).

---

## High-Signal Gotchas

- CRM-backed stream behavior is not the same as fully custom connector-framework ingestion.
- `sf data360 data-stream run` and `sf data360 connection run-existing` are not interchangeable; prefer stream-level refresh for unstructured rescans.
- `SFDC` streams sync on a platform-managed schedule; `data-stream run` is not the general control path for CRM connector refresh.
- Some external database connectors can be created via API while stream creation still requires UI flow or org-specific browser automation. Do not promise a pure CLI stream-creation path for every connector type.
- Initial SharePoint-style unstructured setup can be richer in the UI than in a minimal CLI DLO create flow.
- Stream deletion can also delete the associated DLO unless the delete mode says otherwise.
- DLO field naming differs from CRM field naming, including `__c` → `_c` transformations.
- Query DLO record counts with Data Cloud SQL instead of assuming list output is sufficient.
- `CdpDataStreams` means the stream module is gated for the current org/user; guide the user to provisioning/permissions review instead of retrying blindly.

---

## Output Format

```text
Prepare task: <stream / dlo / transform / docai>
Source: <connection + object>
Target org: <alias>
Artifacts: <stream names / dlo names / json definitions>
Verification: <passed / partial / blocked>
Next step: <harmonize or retrieve>
```

---

## References

- [README.md](README.md)
- [examples/ingestion-api/README.md](examples/ingestion-api/README.md)
- [../orchestrating-datacloud/assets/definitions/data-stream.template.json](../orchestrating-datacloud/assets/definitions/data-stream.template.json)
- [../orchestrating-datacloud/references/plugin-setup.md](../orchestrating-datacloud/references/plugin-setup.md)
- [../orchestrating-datacloud/references/feature-readiness.md](../orchestrating-datacloud/references/feature-readiness.md)
