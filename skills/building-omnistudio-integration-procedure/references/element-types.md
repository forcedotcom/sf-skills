<!-- Parent: building-omnistudio-integration-procedure/SKILL.md -->

# Integration Procedure Element Types Reference

> **Version**: 1.0.0
> **Applies to**: OmniStudio Integration Procedures (Core namespace and Vlocity managed package)

This reference documents every element type available in Integration Procedures, including PropertySetConfig JSON structures, input/output node mapping, and variable scoping rules.

---

## Table of Contents

1. [DataRaptor Extract Action](#1-dataraptor-extract-action)
2. [DataRaptor Load Action](#2-dataraptor-load-action)
3. [DataRaptor Transform Action](#3-dataraptor-transform-action)
4. [Remote Action](#4-remote-action)
5. [Integration Procedure Action](#5-integration-procedure-action)
6. [HTTP Action](#6-http-action)
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
  "disableFlushCacheForGet": false,
  "useQueueableApexRemoting": false,
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
| `disableFlushCacheForGet` | Boolean | No | If true, uses cached DataRaptor results |

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

## 2. DataRaptor Load Action

Writes data to Salesforce objects using a DataRaptor (Data Mapper) Load definition.

### PropertySetConfig

```json
{
  "bundle": "DRLoad_CreateContact",
  "disableFlushCacheForGet": false,
  "useQueueableApexRemoting": false,
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

Always follow a DataRaptor Load with error inspection. Check for:
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

Calls an Apex class method. The Apex class must implement the `vlocity_cmt.VlocityOpenInterface` (managed package) or `omnistudio.VlocityOpenInterface2` (Core namespace) interface.

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
  "useQueueableApexRemoting": false,
  "useFuture": false
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `remoteClass` | String | Yes | Apex class name |
| `remoteMethod` | String | Yes | Method name to invoke |
| `useQueueableApexRemoting` | Boolean | No | If true, executes as a Queueable job (async) |
| `useFuture` | Boolean | No | If true, executes as a future method (async, no return value) |

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
  "ipMethod": "SharedLookup_Standard",
  "additionalInput": {},
  "additionalOutput": {},
  "sendOnlyAdditionalInput": false,
  "responseJSONPath": "",
  "responseJSONNode": "",
  "chainable": false
}
```

### Key Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `ipMethod` | String | Yes | The nested IP's Type_SubType identifier |
| `chainable` | Boolean | No | If true, allows chaining outputs from the nested IP |
| `sendOnlyAdditionalInput` | Boolean | No | If true, only sends `additionalInput` to the nested IP |

### Input Mapping

By default, the entire IP data context is passed to the nested IP. Use `sendOnlyAdditionalInput: true` with `additionalInput` to send only specific data:

```json
{
  "ipMethod": "ContactLookup_Standard",
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

Makes an HTTP callout to an external API endpoint.

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

Conditional Blocks do not use PropertySetConfig in the same way as action elements. Instead, conditions are defined in the element's condition configuration:

### Condition Types

| Condition Type | Description | Example |
|----------------|-------------|---------|
| Value Comparison | Compare two values | `%GetAccount:Industry% EQUALS 'Technology'` |
| Null Check | Check if a value is null/empty | `%GetAccount:Id% IS NOT NULL` |
| Boolean Check | Evaluate a boolean value | `%ValidateInput:isValid% EQUALS true` |
| Group (AND/OR) | Combine multiple conditions | `condition1 AND condition2` |

### Nested Elements

Elements inside a Conditional Block execute only when the condition is true. They follow the same ordering principles as top-level elements.

### If/Else Pattern

Use two Conditional Blocks with complementary conditions:

1. **Conditional Block A**: condition = `%check:value% EQUALS true` -> contains success path elements
2. **Conditional Block B**: condition = `%check:value% NOT EQUALS true` -> contains error/alternate path elements

---

## 8. Loop Block

Iterates over a collection (array) and executes child elements for each item.

### Configuration

| Property | Description |
|----------|-------------|
| Loop collection | JSONPath to the array to iterate over (e.g., `%GetContacts:records%`) |
| Loop element variable | Variable name for the current item in each iteration |

### Child Elements

Elements inside a Loop Block execute once per iteration. The current item is accessible via the loop element variable.

### Performance Considerations

- Minimize the number of elements inside the loop body
- Avoid DataRaptor Extract/Load inside loops (N+1 pattern)
- Prefer bulk operations: collect data in the loop, perform a single DML after the loop
- Set appropriate batch sizes for large collections
- If loop body requires DML, consider using a single DataRaptor Load with a collection input instead

### Example Pattern: Collect and Bulk Process

Instead of:
```
Loop -> DataRaptor Load (per item)  // BAD: N DML operations
```

Use:
```
Loop -> Set Values (collect items into array)
DataRaptor Load (entire array)  // GOOD: 1 DML operation
```

---

## 9. Set Values

Assigns values to variables within the IP context. Used for initialization, response assembly, and data transformation.

### Configuration

Set Values elements define key-value mappings:

| Mapping Type | Description | Example |
|--------------|-------------|---------|
| Static value | Hardcoded constant | `"status": "Processed"` |
| Element reference | Value from upstream element | `"accountName": "%GetAccount:Name%"` |
| Formula | Computed value | Concatenation, conditional expressions |
| Input reference | Value from IP input | `"requestId": "%input:requestId%"` |

### Common Uses

1. **Initialize defaults**: Set default values at the beginning of the procedure
2. **Build output response**: Assemble the final response JSON at the end
3. **Intermediate variables**: Store computed values for use in downstream conditions
4. **Error response**: Build standardized error response objects

### Example: Response Assembly

```
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
| `%elementName:nested.key%` | Reference a nested key using dot notation | `%GetAccount:BillingAddress.City%` |
| `%elementName:array[0]%` | Reference an array element by index | `%GetContacts:records[0].Name%` |
| `%input:key%` | Reference an IP input parameter | `%input:accountId%` |

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
| `useQueueableApexRemoting` | Boolean | `false` | Execute asynchronously via Queueable Apex |
| `disableFlushCacheForGet` | Boolean | `false` | Use cached results if available |

### `responseJSONPath` vs `responseJSONNode`

- `responseJSONPath`: Extracts a subset of the response. For example, `$.records` extracts only the `records` array from the response.
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
