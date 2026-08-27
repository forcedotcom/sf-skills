# Embedded Messaging Code Snippet

After a deployment is created and published, provide the customer with the appropriate code snippet for their deployment type.

---

## Web Deployment — JavaScript Snippet

For Web deployments, embed this JavaScript snippet on the customer's website.

```html
<script type='text/javascript'>
	function initEmbeddedMessaging() {
		try {
			embeddedservice_bootstrap.settings.language = 'en_US'; 
			embeddedservice_bootstrap.init(
				'<ORG_ID>',
				'<EMBEDDED_SERVICE_CONFIG_DEVELOPER_NAME>',
				'<SITE_URL>',
				{
					scrt2URL: '<SCRT2_URL>'
				}
			);
		} catch (err) {
			console.error('Error loading Embedded Messaging: ', err);
		}
	};
</script>
<script type='text/javascript' src='<SITE_URL>/assets/js/bootstrap.min.js' onload='initEmbeddedMessaging()'></script>
```

### Web Parameters

| Parameter | Description | How to obtain |
|-----------|-------------|---------------|
| `SITE_URL` | The Experience Site base URL | From the deployment's `site` field — format: `https://<domain>/ESW_<name>_<timestamp>` |
| `ORG_ID` | The Salesforce Org ID (15-char) | `sf org display --target-org <org-alias> --json` → `result.id` |
| `EMBEDDED_SERVICE_CONFIG_DEVELOPER_NAME` | The deployment's developer name | Same as the `name` / API name used during creation |
| `SCRT2_URL` | The Service Cloud Real Time messaging endpoint | Format: `https://<instance>.salesforce-scrt.com` — obtain from Setup > Embedded Service Deployments |

### Placement

- Place the snippet in the `<body>` of every page where the widget should appear
- For Single Page Applications (SPAs), call `init()` once after the initial page load

---

## API/Mobile Deployment — Configuration JSON

For API and Mobile deployments, provide this configuration JSON for the native app integration.

```json
{
  "OrganizationId": "<ORG_ID>",
  "DeveloperName": "<EMBEDDED_SERVICE_CONFIG_DEVELOPER_NAME>",
  "Url": "<SCRT2_URL>"
}
```

### API/Mobile Parameters

| Parameter | Description | How to obtain |
|-----------|-------------|---------------|
| `ORG_ID` | The Salesforce Org ID (15-char) | `sf org display --target-org <org-alias> --json` → `result.id` |
| `EMBEDDED_SERVICE_CONFIG_DEVELOPER_NAME` | The deployment's developer name | Same as the `name` / API name used during creation |
| `SCRT2_URL` | The Service Cloud Real Time messaging endpoint | Format: `https://<instance>.salesforce-scrt.com` — obtain from Setup > Embedded Service Deployments |

---

## Notes

- The deployment must be **published** before the snippet/config will function
- Web deployments use the JavaScript bootstrap snippet
- API/Mobile deployments use the JSON configuration for native SDK initialization
- If the customer changes the site URL or republishes, the snippet values remain the same unless the deployment is recreated
