# segmenting-datacloud

Audience and insight workflows for Salesforce Data Cloud.

## Use this skill for

- creating and publishing segments
- managing calculated insights
- checking segment counts
- troubleshooting segment SQL
- understanding why a segment is empty or unexpectedly large

## Example requests

```text
"Create a high-value customer segment in Data Cloud"
"Why is my segment returning zero members?"
"Run this calculated insight and help me verify it"
"Show me how to get member counts for this segment"
```

## Common commands

```bash
sf data360 segment list -o myorg 2>/dev/null
sf data360 segment create -o myorg -f segment.json --api-version 64.0 2>/dev/null
sf data360 segment publish -o myorg --name High_Value_Customers 2>/dev/null
sf data360 calculated-insight list -o myorg 2>/dev/null
```

## References

- [SKILL.md](SKILL.md)
- [../orchestrating-datacloud/assets/definitions/calculated-insight.template.json](../orchestrating-datacloud/assets/definitions/calculated-insight.template.json)
- [../orchestrating-datacloud/assets/definitions/segment.template.json](../orchestrating-datacloud/assets/definitions/segment.template.json)
- [CREDITS.md](CREDITS.md)
