# Action Execution — Full Reference

Execute individual Agentforce actions directly against a Salesforce org for testing and debugging.

## Safety Gate (Required)

Before executing ANY action, perform these checks:

### 1. Org Safety Check
Verify the target org is not a production org:
```bash
sf data query --json -q "SELECT IsSandbox FROM Organization" -o <org-alias>
```
If `IsSandbox` is `false`, display a prominent warning:
```
WARNING: Target org is a PRODUCTION org. Running actions against production
can modify real data. Proceed with extreme caution.
```
Ask for explicit confirmation before proceeding on production orgs.

### 2. DML Safety Check
If the action target is a Flow or Apex that performs write operations (CREATE, UPDATE, DELETE),
warn the user and recommend using a sandbox or scratch org first.

### 3. Input Validation
- Do NOT include real PII (SSN, credit card numbers, real email addresses) in test inputs
- Use synthetic test data: `test@example.com`, `000-00-0000`, `4111111111111111`
- If the user provides what appears to be real PII, warn them and suggest synthetic alternatives

## Setup: Get Org Credentials

```bash
# Ensure org is authenticated
sf org display --json -o <org-alias>

# If not authenticated, login first
sf org login web --json --alias <org-alias>

# Extract credentials for API calls
TOKEN=$(sf org display --json -o <org-alias> | jq -r '.result.accessToken')
INSTANCE_URL=$(sf org display --json -o <org-alias> | jq -r '.result.instanceUrl')
```

## Execute a Flow Action

```bash
curl -s "$INSTANCE_URL/services/data/v63.0/actions/custom/flow/Get_Order_Status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs": [{"orderId": "00190000023XXXX"}]}'
```

## Execute an Apex Action

```bash
curl -s "$INSTANCE_URL/services/data/v63.0/actions/custom/apex/OrderProcessor" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs": [{"orderId": "00190000023XXXX", "actionType": "cancel", "reason": "Customer request"}]}'
```

## Execute with JSON Input File

For complex inputs, write a JSON file and pass it to curl:

```bash
cat > /tmp/action-inputs.json << 'EOF'
{
  "inputs": [
    {
      "orderId": "00190000023XXXX",
      "lineItems": [
        {"productId": "01tXX0000008cXX", "quantity": 2, "discount": 0.1}
      ]
    }
  ]
}
EOF

curl -s "$INSTANCE_URL/services/data/v63.0/actions/custom/flow/Process_Return" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/action-inputs.json
```

## Pretty-Print Response

```bash
curl -s "$INSTANCE_URL/services/data/v63.0/actions/custom/flow/Get_Order_Status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs": [{"orderId": "00190000023XXXX"}]}' | jq .
```

## Target Protocols

### Flow Actions (`flow://`)

Executes an Autolaunched Flow via REST API:

```
POST /services/data/v63.0/actions/custom/flow/{flowApiName}
```

Example request body:
```json
{
  "inputs": [
    {
      "orderId": "00190000023XXXX",
      "includeDetails": true
    }
  ]
}
```

Example response:
```json
{
  "actionName": "Get_Order_Status",
  "errors": [],
  "isSuccess": true,
  "outputValues": {
    "orderStatus": "Shipped",
    "trackingNumber": "1Z999AA10123456784",
    "estimatedDelivery": "2024-03-15"
  }
}
```

### Apex Actions (`apex://`)

Executes an @InvocableMethod via REST API:

```
POST /services/data/v63.0/actions/custom/apex/{className}
```

The Apex class must have exactly one method annotated with `@InvocableMethod`.

Example request body:
```json
{
  "inputs": [
    {
      "orderId": "00190000023XXXX",
      "actionType": "cancel"
    }
  ]
}
```

Example response:
```json
{
  "actionName": "OrderProcessor",
  "errors": [],
  "isSuccess": true,
  "outputValues": [
    {
      "success": true,
      "message": "Order cancelled successfully",
      "refundAmount": 299.99
    }
  ]
}
```

## Integration Testing

### Test Flow Pattern

1. **Prepare test data**:
```bash
RECORD_ID=$(sf data create record --json -s Account \
  -v "Name='Test Account' Type='Customer'" \
  -o myorg | jq -r '.result.id')
```

2. **Execute action**:
```bash
curl -s "$INSTANCE_URL/services/data/v63.0/actions/custom/flow/Update_Account" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"inputs\": [{\"accountId\": \"$RECORD_ID\", \"status\": \"Active\"}]}" | jq .
```

3. **Verify results**:
```bash
sf data query --json \
  --query "SELECT Name, Status__c FROM Account WHERE Id = '$RECORD_ID'" \
  -o myorg
```

4. **Clean up**:
```bash
sf data delete record --json -s Account -i $RECORD_ID -o myorg
```

## Debugging

### Retrieve Apex Debug Logs

After executing an Apex action, fetch the most recent debug log:

```bash
sf apex log get --json --number 1 -o <org-alias>
```

### Inspect Available Actions

List all available custom actions to verify deployment:

```bash
# List all Flow actions
curl -s "$INSTANCE_URL/services/data/v63.0/actions/custom/flow" \
  -H "Authorization: Bearer $TOKEN" | jq '.actions[].name'

# List all Apex actions
curl -s "$INSTANCE_URL/services/data/v63.0/actions/custom/apex" \
  -H "Authorization: Bearer $TOKEN" | jq '.actions[].name'
```

## Error Handling

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `NOT_FOUND` | Flow/Apex not found | Verify target name and deployment |
| `INVALID_INPUT` | Input parameter mismatch | Check required inputs in Flow/Apex |
| `INSUFFICIENT_ACCESS` | Permission issue | Verify user permissions |
| `LIMIT_EXCEEDED` | Governor limit hit | Reduce batch size or optimize logic |
| `INVALID_SESSION_ID` | Auth expired | Re-authenticate: `sf org login web` |

### Best Practices

- Check `isSuccess` in the response before processing outputs
- Verify ID format (15 or 18 characters) before sending
- Use `jq` to extract specific fields from responses
- Create and clean up test data to avoid polluting the org
