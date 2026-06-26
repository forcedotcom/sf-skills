# topicName Formats for ManagedEventSubscription

The `<topicName>` field requires a full channel path, not just an API name. The correct format depends on the type of event channel.

## Valid Formats

| Channel type | Format | Example |
|---|---|---|
| Platform event | `/event/<Name>__e` | `/event/Order_Fulfillment__e` |
| Custom platform event channel | `/event/<Name>__chn` | `/event/MyChannel__chn` |
| All-objects change event channel | `/data/ChangeEvents` | `/data/ChangeEvents` |
| Single-object change event | `/data/<Object>ChangeEvent` | `/data/AccountChangeEvent` |
| Custom change event channel | `/data/<Name>__chn` | `/data/MyChangeChannel__chn` |

## Rules

- The path prefix (`/event/` or `/data/`) is required — omitting it causes `"The topicName field is invalid"` deploy error
- The referenced event or channel must exist in the org before deploying the subscription
- `topicName` is immutable after creation — to change it, delete and recreate the subscription

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `The topicName field is invalid` | Missing `/event/` or `/data/` prefix, or wrong suffix | Use the full path format from the table above |
| `The topicName field is invalid` | Referenced event/channel does not exist in the org | Create the platform event or channel first |
