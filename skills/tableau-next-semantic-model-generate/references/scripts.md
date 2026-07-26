# Script Cheat Sheet

Full command reference for every top-level script in `scripts/`. See [SKILL.md](../SKILL.md) for the surrounding workflow context.

**Script Location:** Scripts live under `skills/tableau-next-semantic-model-generate/scripts/` and share library modules from `scripts/_shared/`. Verify with `python scripts/_shared/verify_paths.py`.

## Discovery

```bash
# List all SDMs
python scripts/discover_sdm.py --list

# Inspect SDM structure (objects, fields, calc fields, metrics, RELATIONSHIPS)
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```

## Build an SDM from scratch (anchor + incremental)

```bash
# Create with one anchor data object (prefer __dlm; __dll/__dlc also work)
python scripts/create_sdm.py \
  --api-name {{SDM_NAME}} --label "{{Display Label}}" \
  --data-object {{source__dlm}} --workspace {{WORKSPACE_NAME}}

# Add a data object incrementally (one per call)
python scripts/add_data_object.py --mode object \
  --sdm {{SDM_NAME}} --data-object {{source__dlm}}

# Add a base dimension / measure with a controlled apiName (no auto-suffix)
python scripts/add_data_object.py --mode dimension \
  --sdm {{SDM_NAME}} --object {{OBJECT}} \
  --api-name {{Field_Name}} --source-field {{col__c}} --data-type Text
python scripts/add_data_object.py --mode measure \
  --sdm {{SDM_NAME}} --object {{OBJECT}} \
  --api-name {{Measure_Name}} --source-field {{col__c}} \
  --data-type Number --aggregation Sum

# Add a model-level relationship (join) using RESOLVED apiNames
python scripts/add_relationship.py \
  --sdm {{SDM_NAME}} \
  --left-object {{LEFT_OBJ}} --right-object {{RIGHT_OBJ}} \
  --left-field {{left_suffixed_apiName}} --right-field {{right_suffixed_apiName}} \
  --label "{{Left : Right}}"

# All of the above support --dry-run (print payload without POSTing)
```

## Calculated Fields

```bash
# Create measurement
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type measurement \
  --name {{FIELD_NAME}}_clc \
  --label "{{Display Label}}" \
  --expression "{{TABLEAU_FORMULA}}" \
  --aggregation {{Sum|Avg|UserAgg|Min|Max|Count}}

# Create dimension
python scripts/create_calc_field.py \
  --sdm {{SDM_NAME}} \
  --type dimension \
  --name {{FIELD_NAME}}_clc \
  --label "{{Display Label}}" \
  --expression "{{TABLEAU_FORMULA}}"

# Dry-run (show payload without POSTing)
python scripts/create_calc_field.py ... --dry-run
```

## Metrics

```bash
# Create basic metric
python scripts/create_metric.py \
  --sdm {{SDM_NAME}} \
  --name {{METRIC_NAME}}_mtc \
  --label "{{Display Label}}" \
  --calculated-field {{CALC_FIELD_NAME}}_clc \
  --time-field {{TIME_FIELD}} \
  --time-table {{TABLE_NAME}}

# Create metric with breakdown dimensions
python scripts/create_metric.py \
  --sdm {{SDM_NAME}} \
  --name {{METRIC_NAME}}_mtc \
  --label "{{Display Label}}" \
  --calculated-field {{CALC_FIELD_NAME}}_clc \
  --time-field {{TIME_FIELD}} \
  --time-table {{TABLE_NAME}} \
  --additional-dimension "{{FIELD}}:{{TABLE}}" \
  --additional-dimension "{{FIELD2}}:{{TABLE2}}"

# Dry-run
python scripts/create_metric.py ... --dry-run
```
