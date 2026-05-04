# Scaffold -- Stub Generation Reference

> Extracted from SKILL.md Section 17. This file is loaded on demand when scaffold details are needed.

## Overview

Generates stub metadata files (Flow XML, Apex classes) for Agent Script targets that don't exist in the org, with SObject-aware field discovery when connected.

## Usage

Generate stub metadata files directly using the type mapping and action classification rules below. Parse the `.agent` file to extract action targets and their I/O schemas, then generate Flow XML or Apex classes as appropriate.

For automated scaffold generation, see the [Advanced](#advanced-requires-adlc-repo-clone) section at the bottom.

## What it does

### 1. Discovery Phase (unless --all)
- Runs discover to identify missing targets
- Extracts I/O schemas from the `.agent` file
- Maps Agent Script types to Salesforce types

### 2. Flow Generation (`flow://` targets)
Generates complete Flow XML with input/output variables, assignment placeholders, and start element.

### 3. Apex Generation (`apex://` targets)
Generates Apex class with `@InvocableMethod`, input/output wrapper classes, and test class with 75% coverage boilerplate.

### 4. Action Classification

| Signal | Classification | Generated Files |
|--------|---------------|-----------------|
| "API", "HTTP", "REST", URL | `callout` | Apex + `HttpCalloutMock` test + Remote Site + Custom Metadata |
| "query", "record", "SOQL" | `soql` | Apex with SOQL logic + test |
| No special signals | `basic` | Standard placeholder Apex + test |

### 5. SObject-Aware Generation
When connected to an org:
- Queries SObject metadata for referenced types
- Generates accurate SOQL queries in Apex stubs
- Creates proper field mappings in Flow elements

### 6. Type Mapping

| Agent Script | Flow Type | Apex Type |
|-------------|-----------|-----------|
| `string` | `String` | `String` |
| `number` | `Number` | `Decimal` |
| `boolean` | `Boolean` | `Boolean` |
| `date` | `Date` | `Date` |
| `id` | `String` | `Id` |
| `object` | `Apex` (SObject) | `SObject` |
| `list[string]` | `String` (multipicklist) | `List<String>` |

## Output Structure

```
force-app/main/default/
  flows/
    Get_Order_Status.flow-meta.xml
  classes/
    OrderProcessor.cls
    OrderProcessor.cls-meta.xml
    OrderProcessorTest.cls
    OrderProcessorTest.cls-meta.xml
  permissionsets/
    Agent_Action_Access.permissionset-meta.xml
```

## Best Practices

### Stub Data Quality (CRITICAL for Grounding)

Scaffolded stubs MUST return **realistic-looking data**, not `'TODO'` or empty strings. When the platform LLM invokes an action and gets `'TODO'` back, it has no useful data to present — so it falls back to its training data (SMALL_TALK grounding) or fabricates results (hallucination).

**Evidence:** Comcast eval stubs returned realistic comparison data → 93% grounding rate. JPMorgan eval stubs returned `'TODO'` → 40% grounding rate.

| WRONG | CORRECT |
|-------|---------|
| `res.status = 'TODO';` | `res.status = 'Shipped - In Transit';` |
| `res.summary = '';` | `res.summary = '23 cases open, 8 high-priority, avg resolution 2.3 days';` |
| `res.result = 'TODO: implement';` | `res.result = '{"match_score": 0.92, "case_id": "500ABC"}';` |

**Guidelines for realistic stub data:**
- Use the action description and output field names to infer plausible values
- Include the input values in the response (e.g., `'Order ' + req.order_id + ' is Shipped'`)
- For JSON outputs, return a valid JSON string with all expected fields populated
- For numeric outputs, return non-zero values that make business sense
- For list outputs, return 2-3 sample items

### I/O Variable Matching
Scaffolded stubs MUST have I/O names that **exactly match** the `.agent` file. Case sensitivity matters: `order_id` != `Order_Id` != `orderId`.

### Flow XML Element Ordering (CRITICAL)
All elements of the same type MUST be grouped together. Interleaved elements cause Metadata API rejection.

Recommended order: `apiVersion` -> `description` -> `label` -> `variables` -> `assignments` -> `decisions` -> `recordLookups` -> `recordCreates` -> `recordUpdates` -> `start` -> `status` -> `processType`

### Post-Scaffolding Steps
1. Review generated code (stubs have TODO comments)
2. Add business logic
3. Update test classes with meaningful assertions
4. Add error handling and FLS/CRUD checks

## Backing Logic Selection Criteria

| Criteria | Choose Flow | Choose Apex |
|----------|-------------|-------------|
| Data operations | Simple CRUD, record lookups | Complex queries, bulk ops, cross-object logic |
| External callouts | No callouts needed | REST/SOAP callouts, Named Credentials |
| Business logic | Simple branching, assignments | Complex algorithms, string manipulation |
| Existing assets | Flow already exists | Apex class already exists |
| Maintenance | Admins maintain | Developers maintain |
| Testing | Flow test coverage built-in | Requires Apex test class (75%+ coverage) |

**Rule of thumb:** If the action does a single record lookup or update with no callouts, use Flow. If it involves callouts, complex logic, or bulk operations, use Apex. When in doubt, prefer Apex — it's more debuggable and less constrained.

## Integration Workflow

```bash
# 1. Discover missing targets (CLI-native)
sf api request rest --json "/services/data/v63.0/tooling/query?q=SELECT+DeveloperName+FROM+Flow+WHERE+IsActive=true+AND+ProcessType='AutoLaunchedFlow'" -o myorg
sf api request rest --json "/services/data/v63.0/tooling/query?q=SELECT+Name+FROM+ApexClass+WHERE+Body+LIKE+'%25InvocableMethod%25'" -o myorg
# 2. Generate stubs for missing targets (use type mapping + action classification above)
# 3. Edit stubs with business logic
# 4. Deploy to org
sf project deploy start --json --source-dir force-app/main/default -o myorg
# 5. Verify targets exist
sf api request rest --json "/services/data/v63.0/tooling/query?q=SELECT+DeveloperName+FROM+Flow+WHERE+IsActive=true+AND+ProcessType='AutoLaunchedFlow'" -o myorg
# 6. Publish agent
sf agent publish authoring-bundle --json --api-name MyAgent -o myorg
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All stubs generated |
| 1 | Some stubs failed |
| 2 | Critical failure |

## Advanced (requires ADLC repo clone)

The `scaffold.py` script automates stub generation with SObject-aware field discovery. It is NOT bundled with the skill — requires cloning the ADLC repo.

```bash
# From ADLC repo root — scaffold missing targets (runs discover first)
python3 scripts/scaffold.py \
  --agent-file path/to/Agent.agent -o <org-alias> --output-dir force-app/main/default

# Scaffold all targets without checking org
python3 scripts/scaffold.py \
  --agent-file path/to/Agent.agent --all --output-dir force-app/main/default
```
