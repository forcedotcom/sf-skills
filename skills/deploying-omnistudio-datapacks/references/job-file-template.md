# Vlocity Build Job File Template

Use this as a baseline and keep only settings you need to override.

```yaml
projectPath: .
expansionPath: vlocity

# Optional: narrow export scope
queries:
  - OmniScript
  - IntegrationProcedure
  - DataRaptor
  - FlexCard

# Optional: deterministic targeted scope
# manifest:
#   - Product2/<global-key>
#   - OmniScript/<type>_<subtype>_<language>

# Optional runtime controls
autoUpdateSettings: true
defaultMaxParallel: 1
supportHeadersOnly: true
gitCheck: false
```

## Common command patterns

```bash
# Export
vlocity -sfdx.username <source> -job <job>.yaml packExport

# Deploy
vlocity -sfdx.username <target> -job <job>.yaml packDeploy

# Retry
vlocity -sfdx.username <target> -job <job>.yaml packRetry

# Continue interrupted
vlocity -sfdx.username <target> -job <job>.yaml packContinue
```
