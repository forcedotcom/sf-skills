# sObject field reference — architecture skill

Field reference for the 13 sObjects this skill queries across the 15
SOQL templates under `assets/soql/`. Two are reached via the Data API
(`BotDefinition`, `BotVersion`); the remaining 11 are Tooling-only.

**Source of truth: the live org** (`sf sobject describe --sobject <Name>
[--use-tooling-api]`). Schemas verified against live Salesforce API
v66.0 via `sf sobject describe` on `my-org-alias` + `my-org-alias-2`,
2026-05-02. Official Salesforce Help pages describe logical structures
that frequently diverge from the physical fields the REST / Tooling API
actually expose. When a Help page disagrees with a live describe, trust
the live describe — the names in this reference are what you query.

The source of truth for "mandatory" is `scripts/probe_channels.py`'s
`MANDATORY_FIELDS` map. A probe that sees any `[mandatory]` field
missing flips to `status: "PROBE_FAILED"` — the skill aborts with a
clean error rather than producing a subtly-wrong tree. `[optional]`
fields degrade gracefully — missing ones are recorded but don't block
the run.

---

## Casing gotchas

- **Mixed case is mandatory for `GenAi*` sObjects.** API names are
 `GenAiPlannerDefinition`, `GenAiPluginDefinition`, `GenAiFunctionDefinition`,
 `GenAiPluginFunctionDef`, `GenAiPluginInstructionDef`,
 `GenAiPlannerFunctionDef`, `GenAiPlannerAttrDefinition`. Lowercase
 variants (`genai_planner_definition`, `genaiplannerdefinition`) do not
 resolve. The SOQL parser is case-insensitive on keywords but
 sObject + field names must match the describe output for Tooling API
 calls to route correctly.
- **`GenAiPluginFunctionDef` vs `GenAiPlannerFunctionDef` are different
 tables.** Plugin-scope join (topic → function, via `PluginId`) vs
 planner-bundle-scope join (planner → function, via `PlannerId`). Both
 are 10-field join tables with nearly identical shape; keep them
 straight.
- **`BotVersion.DeveloperName` is the version id, not the version
 label.** `DeveloperName` on BotVersion is the version API name (e.g.
 `v5`), used as the second path segment under
 `<org_id15>/<agent>__<version>/`. `MasterLabel` is the
 human-readable label (e.g. "Version 5 — ported from staging"). Never
 mix them — the data dir layout and the SKILL.md input contract both
 key on `DeveloperName`.
- **`complexvalue` fields require single-row retrieval.** `Metadata`
 (on `Flow`, `FlowDefinition`, `GenAiPluginDefinition`,
 `GenAiFunctionDefinition`), `SymbolTable` (on `ApexClass`), and
 `AgentGraph` (on `GenAiPlannerDefinition`, often null in practice) are
 `complexvalue` types. Salesforce enforces
 `MALFORMED_QUERY: When retrieving results with Metadata or FullName
 fields, the query qualifications must specify no more than one row for
 retrieval.` Batch IN-clause SELECTs that return ≥2 rows fail. Use a
 single-row equality (`WHERE Id = '<id>'`) per fetch; parallelize
 across ids via `concurrent.futures`. `ApexClass.Body` +
 `ApexClass.SymbolTable` is the one notable exception: the
 `Name IN (...)` batch works even though `SymbolTable` is complex.

---

## Cross-sObject join map

Every edge is strictly **forward** from the entry query
(`GenAiPlannerDefinition WHERE DeveloperName = :planner_name`). No
backward lookups.

```
BotDefinition (Data API, PK Id, matched by DeveloperName)
 └── BotVersion (Data API, FK BotDefinitionId)
 │ [resolved to planner name via Bot metadata retrieve]
 ▼
GenAiPlannerDefinition (Tooling, PK Id, matched by DeveloperName)
 │
 ├── GenAiPluginDefinition ← WHERE PlannerId = :plannerId
 │ ├── GenAiPluginInstructionDef ← WHERE GenAiPluginDefinitionId IN (:topic_ids)
 │ ├── GenAiPluginFunctionDef ← WHERE PluginId IN (:topic_ids)
 │ │ └── Function picklist → GenAiFunctionDefinition.Id
 │ └── GenAiFunctionDefinition ← WHERE PluginId IN (:topic_ids)
 │
 ├── GenAiPlannerFunctionDef ← WHERE PlannerId = :plannerId
 │ └── Plugin picklist → GenAiPluginDefinition.Id (or external via retrieve)
 │
 ├── GenAiFunctionDefinition ← WHERE PluginId IN (:topic_ids)
 │ │ (single-query — see functions_by_plugins.soql)
 │ │
 │ └── InvocationTargetType + InvocationTarget route to:
 │ ├── flow → FlowDefinition (batch IN) → Flow.Metadata (parallel single-row)
 │ ├── apex → ApexClass (batch IN, Body + SymbolTable)
 │ ├── standardInvocableAction → (no further fetch — declared only)
 │ └── generatePromptResponse → GenAiPromptTemplate (Metadata API retrieve)
 │
 └── GenAiPlannerAttrDefinition ← WHERE ParentId IN (:function_ids, :planner_id)
 (polymorphic ParentId: GenAiFunctionDefinition OR GenAiPlannerDefinition)
```

Per-channel row counts + `_unresolved[]` reasons are recorded in
`metadata_tree.json` under `_channels` and `_unresolved` keys.

---

## Data API sObjects (2)

### `BotDefinition` (Data API) — one row per agent

Root of the agent metadata. Matched by `DeveloperName`; the rest of the
tree is resolved forward from the `BotVersion` child.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `DeveloperName` | string | no | yes | [mandatory] |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `AgentType` | picklist | yes | yes | [optional] — discriminator for classic vs NGA in some orgs |
| `Type` | picklist | yes | yes | [optional] |
| `AgentTemplate` | string | yes | yes | [optional] — e.g. `SvcCopilotTmpl__EinsteinAgentKind` |
| `BotSource` | picklist | yes | yes | [optional] |
| `AgentUser` | reference | yes | yes | [optional] — FK to `User` |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `LastModifiedDate` | datetime | no | yes | [optional] |
| `SystemModstamp` | datetime | no | yes | [optional] |

### `BotVersion` (Data API) — one row per agent version

Resolves the active version (or user-pinned version) for a given bot.
Parent relationship: `BotDefinition` via `BotDefinitionId`.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `BotDefinitionId` | reference | no | yes | [mandatory] |
| `DeveloperName` | string | no | yes | [optional] — version id (e.g. `v5`) |
| `MasterLabel` | string | yes | yes | [optional] — human label |
| `Status` | picklist | yes | yes | [optional] — `Active` on the current published version |
| `VersionNumber` | int | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `AiReplyRecordVisibility` | picklist | yes | yes | [optional] |
| `ResponseDelayMilliseconds` | int | yes | yes | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `LastModifiedDate` | datetime | no | yes | [optional] |

---

## Tooling API sObjects (11)

All sObjects in this section are reachable via the Tooling API only
(`sf data query --use-tooling-api` or `sf sobject describe --use-tooling-api`).

### `ApexClass` (Tooling) — Apex source + parsed AST

Source + full method/property AST for Apex referenced by
`GenAiFunctionDefinition.InvocationTarget` when
`InvocationTargetType = 'apex'`. Batch-safe on `Name IN (...)` or
`Id IN (...)` (despite `SymbolTable` being `complexvalue`, Salesforce
permits the batch for this particular sObject — verified live).

**Note:** `SymbolTable` is **not part of `FIELDS(ALL)`** and must be
named explicitly in the SELECT.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `Name` | string | no | yes | [mandatory] |
| `Body` | textarea | yes | no | [optional] — full Apex source |
| `SymbolTable` | complexvalue | yes | no | [optional] — parsed AST (methods, params, annotations, line/col) |
| `ApiVersion` | double | no | yes | [optional] |
| `IsValid` | boolean | no | yes | [optional] |
| `Status` | picklist | no | yes | [optional] |
| `LengthWithoutComments` | int | yes | yes | [optional] |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `FullName` | string | yes | no | [optional] — complexvalue companion |
| `Metadata` | complexvalue | yes | no | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `LastModifiedDate` | datetime | no | yes | [optional] |
| `SystemModstamp` | datetime | no | yes | [optional] |

**Single-row requirement for complexvalue columns:** `Metadata` and
`FullName` on `ApexClass` follow the standard `MALFORMED_QUERY` rule —
batch IN-clause SELECTs that return ≥2 rows fail when these two are
selected. `Body` + `SymbolTable` are the exception (batch works).
Comments in `assets/soql/apex_class_bodies_by_ids.soql` +
`apex_class_bodies_by_names.soql` pin this.

### `Flow` (Tooling) — Flow version body

Single-row retrieval required — `Metadata` and `FullName` are both
`complexvalue`. Fired once per `activeVersionId` returned by
`FlowDefinition`; parallelized via `ThreadPoolExecutor`.

**Filterability quirk:** `FullName` is selectable but **not filterable**
(`INVALID_FIELD: field 'FullName' can not be filtered in a query call`).
Filter by `Id` instead.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `DefinitionId` | reference | no | yes | [mandatory] |
| `FullName` | string | yes | **no** | [optional] — complexvalue companion; not filterable |
| `Metadata` | complexvalue | yes | no | [optional] — full flow JSON (actionCalls, subflows, variables, decisions, formulas, assignments, apexPluginCalls) |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `VersionNumber` | int | yes | yes | [optional] |
| `ProcessType` | picklist | yes | yes | [optional] |
| `Status` | picklist | yes | yes | [optional] |
| `ApiVersion` | double | yes | yes | [optional] |
| `IsActive` | boolean | no | yes | [optional] |
| `IsTemplate` | boolean | no | yes | [optional] |
| `RunInMode` | picklist | yes | yes | [optional] |
| `Environments` | picklist | yes | yes | [optional] |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `OverriddenFlowId` | reference | yes | yes | [optional] |
| `SourceTemplateId` | reference | yes | yes | [optional] |
| `TriggerType` | picklist | yes | yes | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `LastModifiedDate` | datetime | no | yes | [optional] |
| `SystemModstamp` | datetime | no | yes | [optional] |
| `InstalledPackageName` | string | yes | yes | [optional] |

**Single-row requirement:** `Metadata` and `FullName` force
`WHERE Id = '<version_id>'`. The SOQL asset `flow_metadata_by_id.soql`
encodes this as a single `Id = '...'` predicate.

### `FlowDefinition` (Tooling) — Flow versioning index

Two-hop feeder to `Flow`. Batch IN-clause works. Returns
`ActiveVersionId` + `LatestVersionId` — the skill prefers active.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `DeveloperName` | string | no | yes | [mandatory] |
| `ActiveVersionId` | reference | yes | yes | [optional] — FK to `Flow.Id` |
| `LatestVersionId` | reference | yes | yes | [optional] — FK to `Flow.Id` |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `Metadata` | complexvalue | yes | no | [optional] — definition-level metadata (may carry what the Flow hop provides on some orgs) |
| `FullName` | string | yes | no | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `LastModifiedDate` | datetime | no | yes | [optional] |
| `SystemModstamp` | datetime | no | yes | [optional] |

### `GenAiPlannerDefinition` (Tooling) — planner root

Entry query for the tree. Matched by `DeveloperName` (the
`<genAiPlannerName>` extracted from the Bot metadata retrieve). The
`PlannerType` picklist is the classifier for classic ReAct vs NGA.

**Seven-value `PlannerType` picklist** (verified consistent across
`my-org-alias`, `my-org-alias-2`, `my-org-alias-3`): grouped by
namespace — `AiCopilot__*` = classic ReAct family,
`Atlas__*` = NGA family. `startswith("Atlas__")` is a clean
classic-vs-NGA discriminator.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `DeveloperName` | string | no | yes | [mandatory] |
| `PlannerType` | picklist | yes | yes | [mandatory] |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `Capabilities` | textarea | yes | no | [optional] — null in every row tested on both classic + NGA |
| `AgentGraph` | complexvalue | yes | no | [optional] — null in every row tested; single-row rule still applies |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `Metadata` | complexvalue | yes | no | [optional] |
| `FullName` | string | yes | no | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `LastModifiedDate` | datetime | no | yes | [optional] |
| `SystemModstamp` | datetime | no | yes | [optional] |

**Single-row requirement for complexvalue columns:** `AgentGraph`,
`Metadata`, `FullName` — select individually; entry query pins
`WHERE DeveloperName = '...' LIMIT 1`.

### `GenAiPluginDefinition` (Tooling) — topics

All topics for a planner via `WHERE PlannerId = :plannerId`. Carries
`PluginType` + `Scope` for topic classification and `CanEscalate` /
`IsLocal` for behavior flags.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `DeveloperName` | string | no | yes | [mandatory] |
| `PluginType` | picklist | yes | yes | [optional] — topic type classifier |
| `Scope` | textarea | yes | no | [optional] — natural-language topic scope |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `CanEscalate` | boolean | yes | yes | [optional] |
| `IsLocal` | boolean | yes | yes | [optional] |
| `Source` | picklist | yes | yes | [optional] |
| `ParentId` | reference | yes | yes | [optional] — planner FK (sometimes referred to as `PlannerId` in SOQL filter clauses) |
| `LocalDeveloperName` | string | yes | yes | [optional] |
| `Language` | picklist | yes | yes | [optional] |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `Metadata` | complexvalue | yes | no | [optional] |
| `FullName` | string | yes | no | [optional] |
| `ClassificationDescription` | textarea | yes | no | [optional] |
| `GenAiFunctionInvoker` | string | yes | yes | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |

**Single-row requirement:** `Metadata` + `FullName` require per-id
retrieval. The production path doesn't SELECT `Metadata` on this sObject
(see `plugins_by_planner.soql`) — it pulls `Scope` + scalar fields
instead, which batch-safely over `PlannerId = :id`.

### `GenAiPluginFunctionDef` (Tooling) — plugin-function join

Join table: `GenAiPluginDefinition` → `GenAiFunctionDefinition`. Batch-
safe on `PluginId IN (...)`.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `PluginId` | reference | no | yes | [mandatory] |
| `Function` | picklist | yes | yes | [optional] — references `GenAiFunctionDefinition.Id` |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `SystemModstamp` | datetime | no | yes | [optional] |

### `GenAiPluginInstructionDef` (Tooling) — per-topic instructions

Per-topic instruction text + ordering. Batch-safe on
`GenAiPluginDefinitionId IN (...)`.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `GenAiPluginDefinitionId` | reference | no | yes | [mandatory] |
| `DeveloperName` | string | no | yes | [optional] |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] — the instruction text |
| `SortOrder` | int | yes | yes | [optional] |
| `Language` | picklist | yes | yes | [optional] |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `FullName` | string | yes | no | [optional] |
| `Metadata` | complexvalue | yes | no | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |

**Single-row requirement:** `Metadata` + `FullName` complexvalue pair;
the production SOQL omits them (scalar fields batch-safely).

### `GenAiFunctionDefinition` (Tooling) — actions

The actions. Combined single-query fetches both bundle-scope (`PlannerId`)
and topic-scope (`PluginId IN`) functions. `InvocationTargetType`
+ `InvocationTarget` route to the downstream fetch (Flow, Apex, prompt,
standard invocable).

**`InvocationTarget` format varies by planner shape** (the ID-prefix
router lives in `scripts/resolve_invocation_target.py`):
- Classic ReAct: DeveloperName string (e.g. `AGNT_SetUserSelectedOption`).
- NGA: Salesforce 15/18-char Id (e.g. `01pVF...` = ApexClass,
 `300VF...` = FlowDefinition, `0hf...` = GenAiPromptTemplate).

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `DeveloperName` | string | no | yes | [mandatory] |
| `InvocationTarget` | string | yes | yes | [mandatory] |
| `InvocationTargetType` | picklist | yes | yes | [optional] — `flow` / `apex` / `standardInvocableAction` / `generatePromptResponse` |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `IsLocal` | boolean | yes | yes | [optional] |
| `IsConfirmationRequired` | boolean | yes | yes | [optional] |
| `IsIncludeInProgressIndicator` | boolean | yes | yes | [optional] |
| `ProgressIndicatorMessage` | string | yes | yes | [optional] |
| `Source` | picklist | yes | yes | [optional] |
| `PluginId` | reference | yes | yes | [optional] — topic-scope FK (null for bundle-scope functions) |
| `PlannerId` | reference | yes | yes | [optional] — bundle-scope FK (null on NGA — attachment is plugin-only) |
| `ParentId` | reference | yes | yes | [optional] |
| `LocalDeveloperName` | string | yes | yes | [optional] |
| `Language` | picklist | yes | yes | [optional] |
| `InvocationTargetApiName` | string | yes | yes | [optional] |
| `MissingValuePromptMessage` | string | yes | yes | [optional] |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `Metadata` | complexvalue | yes | no | [optional] |
| `FullName` | string | yes | no | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |

**Single-row requirement:** `Metadata` + `FullName` complexvalue
columns; production SOQL omits both to keep the `PlannerId / PluginId IN`
batch path intact.

### `GenAiPlannerFunctionDef` (Tooling) — planner-bundle join

Bundle-scope join: planner → function. Analogous to
`GenAiPluginFunctionDef` but keyed on `PlannerId`. Batch-safe on
`PlannerId = :id`.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `PlannerId` | reference | no | yes | [mandatory] |
| `Plugin` | picklist | yes | yes | [optional] — references plugin DeveloperName / id |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |
| `SystemModstamp` | datetime | no | yes | [optional] |

### `GenAiPlannerAttrDefinition` (Tooling) — parameter mappings

The `attributeMappings` — I/O parameter bindings between actions and
the planner. **Polymorphic `ParentId`**: points at either a
`GenAiFunctionDefinition` (function-scope mappings) or
`GenAiPlannerDefinition` (bundle-scope mappings). The production SOQL
passes the union of function ids + planner id via
`WHERE ParentId IN (:function_ids, :planner_id)`.

`MappingType` is the `input` / `output` picklist; `ParameterName`
identifies the bound variable on the planner side.

| Name | Type | Nillable | Filterable | Tag |
|---|---|---|---|---|
| `Id` | id | no | yes | [mandatory] |
| `ParentId` | reference | yes | yes | [optional] — polymorphic: GenAiFunctionDefinition \| GenAiPlannerDefinition |
| `DeveloperName` | string | no | yes | [optional] |
| `MasterLabel` | string | yes | yes | [optional] |
| `Description` | textarea | yes | no | [optional] |
| `MappingType` | picklist | yes | yes | [optional] — `input` / `output` |
| `ParameterName` | string | yes | yes | [optional] |
| `Language` | picklist | yes | yes | [optional] |
| `NamespacePrefix` | string | yes | yes | [optional] |
| `ManageableState` | picklist | yes | yes | [optional] |
| `IsDeleted` | boolean | no | yes | [optional] |
| `CreatedById` | reference | no | yes | [optional] |
| `CreatedDate` | datetime | no | yes | [optional] |
| `LastModifiedById` | reference | no | yes | [optional] |

---

## Known picklist values (live-API verified, 2026-05-02)

| sObject | Field | Values |
|---|---|---|
| `GenAiPlannerDefinition` | `PlannerType` | Seven values split by namespace. Classic family: `AiCopilot__ReAct`, `AiCopilot__ReactAiPlannerV1`, `AiCopilot__SequentialPlannerIntentClassifier`. NGA family: `Atlas__ConcurrentMultiAgentOrchestration`, `Atlas__AnthropicCompatibleV1`, `Atlas__AtlasReactV1`, `Atlas__MainSubAgent` (exact set may vary by release — `startswith("Atlas__")` is the stable classic-vs-NGA discriminator). |
| `GenAiFunctionDefinition` | `InvocationTargetType` | `flow`, `apex`, `standardInvocableAction`, `generatePromptResponse` |
| `GenAiPlannerAttrDefinition` | `MappingType` | `input`, `output` |
| `BotVersion` | `Status` | `Inactive`, `Active` (active = currently published version) |

---

## Mandatory-field enforcement

The `[mandatory]` tags above mirror `scripts/probe_channels.py`:

```python
MANDATORY_FIELDS: Dict[str, set[str]] = {
 "BotDefinition": {"Id", "DeveloperName"},
 "BotVersion": {"Id", "BotDefinitionId"},
 "ApexClass": {"Id", "Name"},
 "Flow": {"Id", "MasterLabel", "DefinitionId"},
 "FlowDefinition": {"Id", "DeveloperName"},
 "GenAiPlannerDefinition": {"Id", "DeveloperName", "PlannerType"},
 "GenAiPluginDefinition": {"Id", "DeveloperName"},
 "GenAiFunctionDefinition": {"Id", "DeveloperName", "InvocationTarget"},
 "GenAiPlannerAttrDefinition": {"Id"},
}
```

`GenAiPluginFunctionDef`, `GenAiPluginInstructionDef`, and
`GenAiPlannerFunctionDef` don't appear in `MANDATORY_FIELDS` — they're
join tables whose `Id` + FK columns are present by construction on
every query. The per-sObject tables above tag their FK columns as
`[mandatory]` because the SOQL assets SELECT them; a probe that saw
them missing would still flip `PROBE_FAILED` via the `Id` check, but
the tag reflects "the skill's SOQL will fail if this column is gone."

When a Salesforce quarterly release renames or removes a
`[mandatory]` field, run with `--reprobe` to force a fresh describe and
surface the drift cleanly.
