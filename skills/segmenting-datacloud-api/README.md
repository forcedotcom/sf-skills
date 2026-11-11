# segmenting-datacloud-api

Manage Salesforce Data Cloud segments via the Connect REST API (`sf api request rest`), without requiring the `sf data360` community plugin.

## Use this skill for

- creating, updating, and deleting segments via REST API
- publishing and deactivating segments
- getting segment details and member lists
- counting segment populations
- full endpoint schema reference (request/response bodies, query params, error codes)

## Example requests

```text
"Create a Dbt segment targeting individuals who purchased in the last 30 days"
"List all active waterfall segments in my org"
"Publish segment 1sgxx00000000PpAAI"
"Get the members of my High_Value_Customers segment"
"Delete the old test segment and recreate it on accounts"
```

## Common commands

```bash
sf api request rest "/services/data/v65.0/ssot/segments" -o myorg
sf api request rest "/services/data/v65.0/ssot/segments" -X POST -H "Content-Type:application/json" -b @/tmp/segment.json -o myorg
sf api request rest "/services/data/v65.0/ssot/segments/My_Segment/actions/publish" -X POST -H "Content-Type:application/json" -b '{}' -o myorg
sf api request rest "/services/data/v65.0/ssot/segments/My_Segment/members?limit=100" -o myorg
```

## References

- [SKILL.md](SKILL.md)
- [CREDITS.md](CREDITS.md)
