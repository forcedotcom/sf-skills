# Vlocity Build Troubleshooting Matrix

| Symptom | Quick checks | Typical fix |
|---|---|---|
| `No match found for ...` | Is referenced key present in exported folder and target org? | Deploy missing dependency first, then `packRetry` |
| `Duplicate Results found for ... GlobalKey` | Query target org for duplicate GlobalKey values | Remove duplicates in target, rerun deploy |
| `Multiple Imported Records ... same Salesforce Record` | Check source for duplicate matching-key combinations | Clean source data, re-export, then redeploy |
| `No Configuration Found` | Was `packUpdateSettings` run recently? | Run `packUpdateSettings` (or keep `autoUpdateSettings: true`) |
| `Some records were not processed` | Compare settings and package versions across orgs | Refresh settings in both orgs, then `packRetry` |
| SASS/template compile errors | Are referenced UI templates exported? | Export missing templates by key and redeploy |

## Retry strategy

1. Run `packRetry`.
2. Check if error count decreases.
3. Repeat until error count plateaus.
4. Fix root data/config issue before further retries.

## Data hygiene checks

```bash
vlocity -sfdx.username <org> -job <job>.yaml validateLocalData
vlocity -sfdx.username <org> -job <job>.yaml packGetDiffs
```
