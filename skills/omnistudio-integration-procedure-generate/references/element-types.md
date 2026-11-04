<!-- Parent: omnistudio-integration-procedure-generate/SKILL.md -->

# Integration Procedure Element Types Reference

> **Version**: 1.0.0
> **Applies to**: OmniStudio Integration Procedures (Core namespace and Vlocity managed package)

This reference documents every element type available in Integration Procedures, including PropertySetConfig JSON structures, input/output node mapping, and variable scoping rules.

---

## Table of Contents

1. [DataRaptor Extract Action](#1-dataraptor-extract-action)
2. [DataRaptor Post Action](#2-dataraptor-post-action)
3. [DataRaptor Transform Action](#3-dataraptor-transform-action)
4. [Remote Action](#4-remote-action)
5. [Integration Procedure Action](#5-integration-procedure-action)
6. [HTTP Action (`Rest Action`)](#6-http-action)
7. [Conditional Block](#7-conditional-block)
8. [Loop Block](#8-loop-block)
9. [Set Values](#9-set-values)
10. [Variable Scoping and Data Passing](#10-variable-scoping-and-data-passing)
11. [PropertySetConfig Common Properties](#11-propertysetconfig-common-properties)

---

## 1. DataRaptor Extract Action

Reads data from Salesforce objects using a DataRaptor (Data Mapper) Extract definition.

### PropertySetConfig

```json
{
  "bundle": "DRExtract_AccountDetails",
  "ignoreCache": false,
  "failOnStepError": false,
  "executionConditionalFormula": "",
  "additionalInput": {},
  "additionalOutput": {},
  "sendOnlyAdditionalInput": false,
  "responseJSONPath": "",
  "responseJSONNode": ""
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | Name of the DataRaptor Extract definition |
| `additionalInput` | Object | No | Extra key-value pairs merged into the DataRaptor input |
| `sendOnlyAdditionalInput` | Boolean | No | If true, only sends `additionalInput`, ignoring upstream data |
| `responseJSONPath` | String | No | JSONPath expression to extract a subset of the response |
| `responseJSONNode` | String | No | Key name to wrap the response under |
| `ignoreCache` | Boolean | No | If true, bypasses cached DataRaptor results |

### Input Mapping

The element receives the IP's current data context. To pass specific values to the DataRaptor:

- Use `additionalInput` to map values from upstream elements:
  ```json
  {
    "additionalInput": {
      "AccountId": "%PreviousElement:accountId%"
    }
  }
  ```

### Output

The DataRaptor's output is stored under the element name in the IP response:

```json
{
  "GetAccountDetails": {
    "Name": "Acme Corp",
    "Industry": "Technology",
    "BillingCity": "San Francisco"
  }
}
```

For multi-record results, the output is an array.

---

## 2. DataRaptor Post Action

Writes data to Salesforce objects using a DataRaptor (Data Mapper) Load definition (element type `DataRaptor Post Action`).

### PropertySetConfig

```json
{
  "bundle": "DRLoad_CreateContact",
  "failOnStepError": false,
  "executionConditionalFormula": "",
  "additionalInput": {},
  "additionalOutput": {},
  "sendOnlyAdditionalInput": false,
  "responseJSONPath": "",
  "responseJSONNode": ""
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | Name of the DataRaptor Load definition |
| `additionalInput` | Object | No | Extra key-value pairs merged into the DataRaptor input |
| `sendOnlyAdditionalInput` | Boolean | No | If true, only sends `additionalInput` as input |

### Input Mapping

Map upstream data into the fields the DataRaptor Load expects:

```json
{
  "additionalInput": {
    "FirstName": "%SetInputValues:firstName%",
    "LastName": "%SetInputValues:lastName%",
    "AccountId": "%GetAccountDetails:Id%"
  }
}
```

### Output

Returns the result of the DML operation:

```json
{
  "CreateContact": {
    "Id": "003XXXXXXXXXXXX",
    "errors": [],
    "success": true
  }
}
```

### Error Handling

Always follow a DataRaptor Post Action with error inspection. Check for:
- `success` field (boolean)
- `errors` array (contains error objects with `statusCode` and `message`)

---

## 3. DataRaptor Transform Action

Reshapes data without making any Salesforce queries or DML. Uses a DataRaptor Transform definition to map fields between JSON structures.

### PropertySetConfig

```json
{
  "bundle": "DRTransform_FlattenAddress",
  "additionalInput": {},
  "additionalOutput": {},
  "sendOnlyAdditionalInput": false,
  "responseJSONPath": "",
  "responseJSONNode": ""
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | Name of the DataRaptor Transform definition |
| `additionalInput` | Object | No | Extra key-value pairs to include in the transform input |

### Use Cases

- Flatten nested JSON structures for downstream processing
- Rename fields to match external API contracts
- Combine data from multiple upstream elements into a single structure
- Extract specific fields from a large response

### Input/Output

Input: The full IP data context or specific values via `additionalInput`
Output: The transformed JSON structure, stored under the element name

---

## 4. Remote Action

Calls an Apex class method. The Apex class must implement `System.Callable` or `omnistudio.VlocityOpenInterface` / `omnistudio.VlocityOpenInterface2` (`vlocity_cmt.` / `vlocity_ins.` in Vlocity managed-package orgs).

### PropertySetConfig

```json
{
  "remoteClass": "AccountValidationService",
  "remoteMethod": "validateAccount",
  "additionalInput": {},
  "additionalOutput": {},
  "sendOnlyAdditionalInput": false,
  "responseJSONPath": "",
  "responseJSONNode": "",
  "remoteOptions": {},
  "failOnStepError": false
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `remoteClass` | String | Yes | Apex class name |
| `remoteMethod` | String | Yes | Method name to invoke |
| `remoteOptions` | Object | No | Passed to the class as `options` |
| `failOnStepError` | Boolean | No | Stop the IP if this step fails |

### Apex Interface

The Apex class must follow this pattern:

```apex
// Core namespace
global class AccountValidationService implements omnistudio.VlocityOpenInterface2 {
    global Object invokeMethod(
        String methodName,
        Map<String, Object> inputMap,
        Map<String, Object> outputMap,
        Map<String, Object> options
    ) {
        if (methodName == 'validateAccount') {
            // Business logic here
            String accountId = (String) inputMap.get('AccountId');
            // ... validation logic ...
            outputMap.put('isValid', true);
            outputMap.put('validationMessages', new List<String>());
        }
        return null;
    }
}
```

### Input Mapping

The IP data context is passed as `inputMap`. Use `additionalInput` to add or override values:

```json
{
  "additionalInput": {
    "AccountId": "%GetAccountDetails:Id%",
    "validationType": "full"
  }
}
```

### Output

The `outputMap` contents are stored under the element name:

```json
{
  "ValidateAccount": {
    "isValid": true,
    "validationMessages": []
  }
}
```

---

## 5. Integration Procedure Action

Calls another Integration Procedure. Enables composition and reuse of IP logic.

### PropertySetConfig

```json
{
  "integrationProcedureKey": "SharedLookup_Standard",
  "additionalInput": {},
  "additionalOutput": {},
  "sendOnlyAdditionalInput": false,
  "responseJSONPath": "",
  "responseJSONNode": "",
  "disableChainable": false
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `integrationProcedureKey` | String | Yes | The nested IP's Type_SubType identifier |
| `disableChainable` | Boolean | No | If true, the nested IP does not chain (runs within the caller's limits) |
| `sendOnlyAdditionalInput` | Boolean | No | If true, only sends `additionalInput` to the nested IP |

### Input Mapping

By default, the entire IP data context is passed to the nested IP. Use `sendOnlyAdditionalInput: true` with `additionalInput` to send only specific data:

```json
{
  "integrationProcedureKey": "ContactLookup_Standard",
  "sendOnlyAdditionalInput": true,
  "additionalInput": {
    "accountId": "%GetAccountDetails:Id%"
  }
}
```

### Output

The nested IP's full response is stored under the calling element's name:

```json
{
  "LookupContacts": {
    "contacts": [...],
    "totalCount": 5
  }
}
```

### Circular Dependency Prevention

Before configuring an IP Action, verify that the target IP does not call back to the current IP (directly or through intermediaries). Circular calls cause stack overflow errors at runtime.

---

## 6. HTTP Action

Makes an HTTP callout to an external API endpoint. The element's `Type` value is `Rest Action`.

### PropertySetConfig

```json
{
  "path": "https://api.example.com/v1/accounts",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer %GetToken:accessToken%"
  },
  "body": {},
  "additionalInput": {},
  "additionalOutput": {},
  "sendOnlyAdditionalInput": false,
  "responseJSONPath": "",
  "responseJSONNode": "",
  "namedCredential": "",
  "timeout": 30000
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `path` | String | Yes | Full URL or relative path (if using Named Credential) |
| `method` | String | Yes | HTTP method: GET, POST, PUT, PATCH, DELETE |
| `headers` | Object | No | Request headers as key-value pairs |
| `body` | Object | No | Request body (for POST/PUT/PATCH) |
| `namedCredential` | String | No | Salesforce Named Credential for authentication |
| `timeout` | Number | No | Request timeout in milliseconds |

### Security Best Practices

- Use Named Credentials for API authentication instead of hardcoded tokens
- Reference tokens from upstream elements (e.g., OAuth token retrieval) using `%elementName:key%` syntax
- Never store API keys in PropertySetConfig — use Custom Settings or Custom Metadata

### Input Mapping

Use `additionalInput` to build dynamic request bodies:

```json
{
  "body": {
    "accountName": "%GetAccountDetails:Name%",
    "externalId": "%InputData:externalId%"
  }
}
```

### Output

The HTTP response is stored under the element name:

```json
{
  "CallExternalAPI": {
    "statusCode": 200,
    "body": {
      "result": "success",
      "externalRecordId": "EXT-12345"
    }
  }
}
```

### Error Handling

Check `statusCode` in a downstream Conditional Block:

- 2xx: Success, proceed
- 4xx: Client error, log and return error response
- 5xx: Server error, consider retry or graceful degradation

---

## 7. Conditional Block

Evaluates conditions and branches execution based on the result. Contains child elements that execute only when the condition evaluates to true.

### Configuration

The condition is a formula in `executionConditionalFormula` (the same property every IP element has for conditional execution). `isIfElseBlock: true` turns the block into an if / else-if / else container.

```json
{
  "executionConditionalFormula": "%ActionType% == \"New\" || %ActionType% == \"Edit\"",
  "isIfElseBlock": false
}
```

### Condition Types

IP formulas use `==`, `!=`, `>`, `<`, `&&`, `||` to combine conditions. For the functions available in IP formulas see `formula-functions.md`.

| Condition Type | Description | Example |
|----------------|-------------|---------|
| Value Comparison | Compare two values | `%GetAccount:Industry% == "Technology"` |
| Null Check | Check if a value is null/empty | `ISNOTBLANK(%GetAccount:Id%)` |
| Boolean Check | Evaluate a boolean value | `%ValidateInput:isValid% == true` (or just `%ValidateInput:isValid%`) |
| Group (AND/OR) | Combine multiple conditions | `condition1 && condition2`, `condition1 \|\| condition2` |

### Nested Elements

Elements inside a Conditional Block execute only when the condition is true. They follow the same ordering principles as top-level elements.

### If/Else Pattern

Use two Conditional Blocks with complementary conditions:

1. **Conditional Block A**: condition = `%check:value% == true` -> contains success path elements
2. **Conditional Block B**: condition = `%check:value% != true` -> contains error/alternate path elements

(Or a single Conditional Block with `isIfElseBlock: true` containing the branches.)

---

## 8. Loop Block

Iterates over a collection (array) and executes child elements for each item.

### Configuration

| Property | Description |
|----------|-------------|
| `loopList` | Data JSON path (no `%`) to the array to iterate over (e.g., `GetContacts:records`) |
| `loopOutput` | Map of keys to collect from each iteration (e.g., `{ "SetItem": "%SetItem%" }`) |

### Child Elements

Elements inside a Loop Block execute once per iteration. The current item is accessible under the `loopList` path (e.g., `%GetContacts:records:Name%` inside the loop refers to the current record).

### Performance Considerations

- Minimize the number of elements inside the loop body
- Avoid DataRaptor Extract/Load inside loops (N+1 pattern)
- Prefer bulk operations: collect data in the loop, perform a single DML after the loop
- Set appropriate batch sizes for large collections
- If loop body requires DML, consider using a single DataRaptor Load with a collection input instead

### Example Pattern: Collect and Bulk Process

Instead of:
```text
Loop -> DataRaptor Post Action (per item)  // BAD: N DML operations
```

Use:
```text
Loop -> Set Values (collect items into array)
DataRaptor Post Action (entire array)  // GOOD: 1 DML operation
```

---

## 9. Set Values

Assigns values to variables within the IP context. Used for initialization, response assembly, and data transformation.

### Configuration

Set Values elements define key-value mappings in `elementValueMap`. Prefix a value with `=` to evaluate it as a formula (e.g. `"=YEAR(TODAY())"`, `"=%A% + 1"`). Supported functions: `formula-functions.md`.

| Mapping Type | Description | Example |
|--------------|-------------|---------|
| Static value | Hardcoded constant | `"status": "Processed"` |
| Element reference | Value from upstream element | `"accountName": "%GetAccount:Name%"` |
| Formula | Computed value | `"fullName": "=CONCATENATE(%First%, \" \", %Last%)"` |
| Input reference | Value from IP input (input keys are top-level in the data JSON) | `"requestId": "%requestId%"` |

### Common Uses

1. **Initialize defaults**: Set default values at the beginning of the procedure
2. **Build output response**: Assemble the final response JSON at the end
3. **Intermediate variables**: Store computed values for use in downstream conditions
4. **Error response**: Build standardized error response objects

### Example: Response Assembly

```text
Set Values: "BuildResponse"
  out_success = true
  out_accountId = %GetAccount:Id%
  out_contactCount = %GetContacts:totalSize%
  out_status = "Complete"
```

---

## 10. Variable Scoping and Data Passing

### Scope Rules

| Scope Level | Visibility | Lifetime |
|-------------|------------|----------|
| IP Input | All elements | Entire execution |
| Element Output | All downstream elements | Entire execution |
| Set Values Variable | All downstream elements | Entire execution |
| Loop Variable | Elements inside the loop body | Current iteration |
| Conditional Block Variable | Elements inside the block | Block execution |
| Nested IP Output | Calling element and downstream | Entire execution (under element name) |

### Data Context

The IP maintains a cumulative data context. Each element's output is added to this context under the element's name. Downstream elements can reference any upstream element's output.

### Reference Syntax

| Syntax | Description | Example |
|--------|-------------|---------|
| `%elementName:key%` | Reference a specific key from an element's output | `%GetAccount:Name%` |
| `%elementName:nested:key%` | Reference a nested key (`:` between nodes) | `%GetAccount:BillingAddress:City%` |
| `%elementName:array\|N%` | Reference an array element by 1-based index (`\|1`, `\|2`, …) — not `[0]` | `%GetContacts:records\|1:Name%` |
| `%key%` | Reference an IP input parameter (input is merged at the top level of the data JSON) | `%accountId%` |

### Data Passing to Nested IPs

When calling a nested IP via Integration Procedure Action:

- **Default**: The entire data context is passed as input
- **Selective**: Use `sendOnlyAdditionalInput: true` + `additionalInput` to pass specific values
- **Output**: The nested IP's response is namespaced under the calling element's name

### Data Passing Best Practices

- Use `sendOnlyAdditionalInput: true` for nested IP calls to avoid leaking unnecessary data
- Keep variable names consistent across elements for readability
- Document the expected data shape at each stage of the procedure
- Use Set Values to explicitly name and scope intermediate results rather than relying on implicit context merging

---

## 11. PropertySetConfig Common Properties

These properties are available on most action elements:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `additionalInput` | Object | `{}` | Extra key-value pairs added to the element's input |
| `additionalOutput` | Object | `{}` | Extra key-value pairs added to the element's output |
| `sendOnlyAdditionalInput` | Boolean | `false` | If true, only `additionalInput` is sent (upstream context excluded) |
| `responseJSONPath` | String | `""` | JSONPath to extract a subset of the element's response |
| `responseJSONNode` | String | `""` | Key name to wrap the response under |
| `executionConditionalFormula` | String | `""` | Run the element only when the formula is true |
| `failOnStepError` | Boolean | `false` | Stop the IP if this element fails |
| `failureConditionalFormula` | String | `""` | Formula that marks the step as failed |
| `sendJSONPath` / `sendJSONNode` | String | `""` | Send a sub-node of the data JSON / wrap it under a key |
| `chainOnStep` | Boolean | `false` | Chain (new transaction) at this step |

### `responseJSONPath` vs `responseJSONNode`

- `responseJSONPath`: Extracts a subset of the response. For example, `records` extracts only the `records` array from the response (plain data JSON path with `:` separators — no `$.`).
- `responseJSONNode`: Wraps the response under a named key. For example, setting `responseJSONNode` to `accountData` wraps the entire response under `{"accountData": {...}}`.

These can be combined: first extract via path, then wrap under a node name.

### `additionalInput` Merge Behavior

When `sendOnlyAdditionalInput` is false (default):
1. The IP's current data context is used as the base input
2. `additionalInput` key-value pairs are merged into this context
3. If a key exists in both, `additionalInput` takes precedence (override)

When `sendOnlyAdditionalInput` is true:
1. The data context is ignored
2. Only `additionalInput` key-value pairs are sent as input
3. Use this for nested IP calls where you want a clean input boundary
