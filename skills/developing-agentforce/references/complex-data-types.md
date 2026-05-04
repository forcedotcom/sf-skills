<!-- Parent: adlc-author/SKILL.md -->

# `complex_data_type_name` Mapping Table

> **"#1 source of compile errors"** - Use this table when defining action inputs/outputs in Agentforce Assets.

## Decision Tree: When Do I Need `complex_data_type_name`?

1. **Variable** with `number`? → Use `number` directly, no complex type needed
2. **Action I/O** with integer value, **Flow target** (`flow://`)? → Use `object` + `complex_data_type_name: "lightning__numberType"`
3. **Action I/O** with integer value, **Apex target** (`apex://`)? → Use `object` + `complex_data_type_name: "lightning__integerType"`
4. **Action input/output** with decimal value? → Use `object` + `complex_data_type_name: "lightning__doubleType"`
5. **Variable** with any other primitive? → Use the type directly (`string`, `boolean`, `date`)
6. **Action I/O** with non-primitive? → Use `object` + appropriate `complex_data_type_name` from table below

> **Key insight:** Bare `number` works in **variable declarations** but **fails at publish** in action inputs/outputs. This is the #1 cause of publish-fix-republish cycles.

> **CRITICAL: Target type matters!** The valid `complex_data_type_name` for integer values differs by target type:
> - **Flow targets** (`flow://`): Use `lightning__numberType` (NOT `lightning__integerType`)
> - **Apex targets** (`apex://`): Use `lightning__integerType` (NOT `lightning__numberType`)
> Using the wrong one causes a publish validation error.

## Full Mapping Table

| Data Type | `complex_data_type_name` Value | Notes |
|-----------|-------------------------------|-------|
| `string` | *(none needed)* | Primitive type — works in both variables and action I/O |
| `number` (variable only) | *(none needed)* | **Variables only** — do NOT use bare `number` in action I/O |
| `boolean` | *(none needed)* | Primitive type |
| `object` (SObject) | `lightning__recordInfoType` | Use for Account, Contact, etc. |
| `list[string]` | `lightning__textType` | Collection of text values |
| `list[object]` | `lightning__textType` | Serialized as JSON text |
| Apex Inner Class | `@apexClassType/NamespacedClass__InnerClass` | Namespace required |
| Custom LWC Type | `lightning__c__CustomTypeName` | Custom component types |
| Currency field | `lightning__currencyType` | For monetary values |
| `datetime` | `lightning__dateTimeStringType` | DateTime values |
| `integer` | `lightning__integerType` | Integer numbers (action I/O only) |
| `double` / `number` | `lightning__doubleType` | Decimal/floating-point numbers (action I/O only) |
| `object` (structured) | `lightning__objectType` | Complex data structures (action I/O only) |
| `list` (generic) | `lightning__listType` | Arrays/lists (action I/O only) |

> **Naming variance**: Upstream documentation uses `lightning__dateTimeType` while testing confirms `lightning__dateTimeStringType`. Both may be valid depending on API version — use `lightning__dateTimeStringType` as the tested default.

## Agent Script → Lightning Type Mapping

> Use this when troubleshooting type errors between Agent Script action I/O and Apex/Flow targets.

| Agent Script Type | Lightning Type | Apex Type | Notes |
|-------------------|---------------|-----------|-------|
| `string` | `lightning__textType` | `String` | No `complex_data_type_name` needed |
| `number` | `lightning__numberType` | `Decimal` / `Double` | No `complex_data_type_name` needed |
| `boolean` | `lightning__booleanType` | `Boolean` | No `complex_data_type_name` needed |
| `datetime` | `lightning__dateTimeStringType` | `DateTime` | **Actions only** — not valid for variables |
| `date` | `lightning__dateType` | `Date` | Valid for both variables and actions |
| `currency` | `lightning__currencyType` | `Decimal` | Annotated with currency type |

**Pro Tip**: Don't manually edit `complex_data_type_name` - use the UI dropdown in **Agentforce Assets > Action Definition**, then export/import the action definition.