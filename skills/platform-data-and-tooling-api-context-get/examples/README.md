# Salesforce Data + Tooling API - Section-Specific Loading Examples

This directory contains working code examples demonstrating how to
programmatically load only the sections you need from the enterprise
(SOQL/DML sObject) and Tooling (developer record) JSON files, and how to
traverse this skill's surface-specific structure.

## Critical Warning

**NEVER load these JSON files whole (Read, cat, whole-file `JSON.parse`)!**

Enterprise sObjects like `Account.json` carry a large `wsdl_segment` and a
separate `field_reference` catalog. Loading the entire file wastes 60-80% of
tokens. Extract only the section you need.

## Structure this skill exposes

- **`assets/enterprise_api/`** — standard sObjects you query with SOQL
  and modify with DML (custom `__c` objects are not included — describe the
  live org for those). `fields` entries carry `properties`
  (Create/Filter/Sort/Group/Nillable/Update) plus relationship metadata
  (`relationship_name`, `refers_to`, `relationship_type`).
- **`assets/tooling_api/`** — developer/diagnostics records (ApexClass,
  TraceFlag, EntityDefinition, ...). Expose `supported_rest_api_http_methods`
  / `supported_soap_calls`; queried via `/services/data/vXX.0/tooling/query`.
- **`fields` vs `field_reference`** — `field_reference` is a SEPARATE catalog,
  **not a subset** of `fields`. System/audit fields (Id, CreatedDate, ...)
  frequently live ONLY in `field_reference`. If a field isn't in `fields`,
  check `field_reference` before concluding it doesn't exist.

## Available Examples

### 1. Python Example
**File**: [`python_section_loading.py`](./python_section_loading.py)

**Usage**:
```bash
python3 examples/python_section_loading.py
```

**Key Pattern** (respect field properties before writing SOQL):
```python
import json
with open('assets/enterprise_api/Opportunity.json') as f:
    data = json.load(f)
filterable = [n for n, m in data['fields'].items()
              if 'filter' in (m.get('properties', '') or '').lower()]
```

### 2. JavaScript/Node.js Example
**File**: [`javascript_section_loading.js`](./javascript_section_loading.js)

**Usage**:
```bash
node examples/javascript_section_loading.js
```

### 3. Bash + jq Example
**File**: [`bash_section_loading.sh`](./bash_section_loading.sh)

**Usage**:
```bash
bash examples/bash_section_loading.sh
```

**Key Pattern** (check BOTH catalogs):
```bash
# Fields present ONLY in field_reference (not in fields):
jq -r '[(.field_reference | keys[]) as $k
         | select((.fields | has($k)) | not) | $k][:5][]' \
   assets/enterprise_api/Account.json
```

## What every example demonstrates

1. Load only the `fields` section from an enterprise sObject
2. Find **filterable** fields (WHERE-safe) via the `properties` string
3. Traverse a relationship (`relationship_name` / `refers_to`)
4. Check **both** `fields` and `field_reference` (dual catalog)
5. Read a Tooling record's `supported_rest_api_http_methods`

## Property → SOQL/DML capability

| `properties` token | Enables |
|--------------------|---------|
| `Filter`           | `WHERE` clause |
| `Sort`             | `ORDER BY` |
| `Group`            | `GROUP BY` |
| `Create`           | `insert` DML |
| `Update`           | `update` DML |
| `Nillable`         | may be null (else required on insert) |

A field without the needed token fails at runtime — verify before querying.
