# Update Constraints for ManagedEventSubscription

## Fields That Can Be Updated

| Field | Notes |
|-------|-------|
| `<label>` | Can be changed at any time |
| `<state>` | Toggle between `RUN` and `STOP` — `PAUSE` is reserved for internal use and will be rejected |
| `<defaultReplay>` | Can be changed, but see warning below |
| `<errorRecoveryReplay>` | Can be changed at any time |

## Fields That Cannot Be Changed After Creation

| Field | Why |
|-------|-----|
| `<topicName>` | Changing the channel requires delete + recreate; the platform ties replay state to the original channel |
| DeveloperName (filename) | Renaming requires delete + recreate; rename-in-place is not supported by the Metadata API |

## defaultReplay Change Warning

Changing `<defaultReplay>` from `LATEST` to `EARLIEST` on an existing subscription will cause it to re-replay all available events from the earliest retained position on the next activation. On high-volume event channels this can create a large backlog. Always confirm intent with the user before making this change.

## Procedure for Immutable Field Changes

If the user needs to change `<topicName>` or DeveloperName:

1. Export current subscription config
2. Delete the existing subscription (see `references/delete-guide.md`)
3. Create a new subscription with the desired values
4. Note: replay tracking state from the old subscription is lost
