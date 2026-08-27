# Creating Web ESD via Connect API

Web-type Embedded Service Deployments cannot be created via Metadata API due to a circular dependency between Network and CustomSite metadata types. Use Connect API instead.

---

## Prerequisites

1. Digital Experiences must be enabled in the org (Setup > Digital Experiences > Enable)
2. The messaging channel must already exist (need the `messagingChannelId` — the 18-char record ID)
3. Salesforce CLI (`sf`) must be authenticated to the target org

---

## Connect API Endpoint

```text
POST /connect/embeddedmessaging/deployment/setup
```

### Request Body (Web)

```json
{
  "name": "<DEPLOYMENT_API_NAME>",
  "masterLabel": "<DEPLOYMENT_LABEL>",
  "deploymentType": "Web",
  "clientVersion": "WebV2",
  "hostDomain": "<HOST_DOMAIN>",
  "messagingChannelId": "<MESSAGING_CHANNEL_ID>"
}
```

### Request Body (API / Mobile)

```json
{
  "name": "<DEPLOYMENT_API_NAME>",
  "masterLabel": "<DEPLOYMENT_LABEL>",
  "deploymentType": "API",
  "messagingChannelId": "<MESSAGING_CHANNEL_ID>"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | API name for the deployment (no spaces) |
| `masterLabel` | String | Yes | Display label for the deployment |
| `deploymentType` | String | Yes | `Web`, `API`, or `Mobile` |
| `messagingChannelId` | String | Yes | 18-character record ID of the messaging channel |
| `clientVersion` | String | Web only | Always `WebV2` for enhanced messaging web deployments |
| `hostDomain` | String | Web only | The domain where the widget will be hosted (e.g. `mysite.com`) |

### Using Salesforce CLI (Web)

```bash
sf api request rest \
  --method POST \
  --url "/connect/embeddedmessaging/deployment/setup" \
  --body '{"name":"<NAME>","masterLabel":"<LABEL>","deploymentType":"Web","clientVersion":"WebV2","hostDomain":"<DOMAIN>","messagingChannelId":"<CHANNEL_ID>"}' \
  --target-org <org-alias>
```

### Using Salesforce CLI (API / Mobile)

```bash
sf api request rest \
  --method POST \
  --url "/connect/embeddedmessaging/deployment/setup" \
  --body '{"name":"<NAME>","masterLabel":"<LABEL>","deploymentType":"API","messagingChannelId":"<CHANNEL_ID>"}' \
  --target-org <org-alias>
```

### Getting the Messaging Channel ID

Query the messaging channel ID by developer name:

```bash
sf data query \
  --query "SELECT Id FROM MessagingChannel WHERE DeveloperName = '<CHANNEL_PLATFORM_KEY>'" \
  --target-org <org-alias>
```

---

## Response

```json
{
  "isSuccess": true,
  "embeddedServiceDeploymentId": "0Mbxx0000000001",
  "isPublishSuccess": true,
  "errorMsg": null
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `isSuccess` | Boolean | Whether the deployment was successfully created |
| `embeddedServiceDeploymentId` | String | 18-character record ID of the created deployment |
| `isPublishSuccess` | Boolean | Whether the deployment was successfully published |
| `errorMsg` | String | Error message if creation or publish failed (null on success) |

Save the `embeddedServiceDeploymentId` — it identifies the deployment for subsequent updates.

---

## Post-Creation Steps

After creating the Web ESD via Connect API:

1. **Update via Metadata API** — deploy `EmbeddedServiceConfig` XML with full configuration (forms, branding, channel settings, T&C)
2. **Publish** — make changes live via Connect API publish endpoint

---

## Publishing After Updates

After any update to a Web ESD (branding, forms, labels, settings), publish to make changes live:

```text
POST /connect/embeddedservice/embeddedserviceconfig/publish/<EMBEDDED_SERVICE_CONFIG_ID>
```

```bash
sf api request rest \
  /services/data/v67.0/connect/embeddedservice/embeddedserviceconfig/publish/<EMBEDDED_SERVICE_CONFIG_ID> \
  --method POST \
  --target-org <org-alias>
```

---

## Known Limitations

- Site name is auto-generated — cannot be customized during creation
- The site format is always `ESW_<name>_<timestamp>`
- Web ESD creation is not idempotent — calling twice creates duplicate deployments
- Connect API does not support configuring forms, branding, or toggles at creation time — use Metadata API update afterward
- `messagingChannelId` requires querying the record ID (not the developer name)
