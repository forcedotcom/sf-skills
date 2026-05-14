# activating-datacloud

Activation and downstream delivery workflows for Salesforce Data Cloud.

## Use this skill for

- activations
- activation targets
- data actions
- data action targets
- downstream platform inspection before push

## Example requests

```text
"Activate this segment to the downstream platform"
"Show me what activation targets already exist"
"Create a data action target for this integration"
"Help me inspect why this activation is not ready"
```

## Common commands

```bash
sf data360 activation platforms -o myorg 2>/dev/null
sf data360 activation-target list -o myorg 2>/dev/null
sf data360 activation list -o myorg 2>/dev/null
sf data360 data-action-target list -o myorg 2>/dev/null
```

## References

- [SKILL.md](SKILL.md)
- [../orchestrating-datacloud/assets/definitions/activation-target.template.json](../orchestrating-datacloud/assets/definitions/activation-target.template.json)
- [../orchestrating-datacloud/assets/definitions/activation.template.json](../orchestrating-datacloud/assets/definitions/activation.template.json)
- [../orchestrating-datacloud/assets/definitions/data-action-target.template.json](../orchestrating-datacloud/assets/definitions/data-action-target.template.json)
- [../orchestrating-datacloud/assets/definitions/data-action.template.json](../orchestrating-datacloud/assets/definitions/data-action.template.json)
- [../orchestrating-datacloud/references/plugin-setup.md](../orchestrating-datacloud/references/plugin-setup.md)
- [CREDITS.md](CREDITS.md)
