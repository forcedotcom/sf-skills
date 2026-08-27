# Sample SOP Excerpt

This is a representative slice of a customer SOP — the type of input the
skill receives. The matching expected output is in
`sample_sop_to_config.json`.

---

## Post Refresh Steps – Update Outbound Messages Endpoints

Update the Outbound Messaging Endpoints after the refresh. Navigate to
Setup > Process Automation > Workflow Actions > Outbound Messages.

| Outbound Message       | Post-refresh endpoint URL                       |
|------------------------|-------------------------------------------------|
| `IR_Account_OBM_PROD`  | `https://uat.example.com/services/account`      |
| `IR_Contact_OBM_PROD`  | `https://uat.example.com/services/contact`      |
| `IR_Asset_OBM_PROD`    | `https://uat.example.com/services/asset`        |

The OBM names embed the target SObject (`Account`, `Contact`, `Asset`),
which becomes the mandatory `Object` field on each generated entry.

## Post Refresh Steps – Remote Site Settings

Update the Remote Site Settings under Setup > Security > Remote Site
Settings. Both should remain Active.

| Remote Site Name   | Post-refresh URL                       |
|--------------------|----------------------------------------|
| `R12_Remote_Site`  | `https://uat.example.com`              |
| `Tavant_API`       | `https://tavant.uat.example.com`       |
