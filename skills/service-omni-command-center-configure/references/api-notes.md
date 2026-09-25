# Command Center for Service V2 API notes

## Metadata contract

Core work item `W-24039822` and Core PR `#16874` expose these fields on `Settings:OmniChannel`:

| Metadata field | Product control |
|---|---|
| `enableCommandCenterForServiceV2` | Command Center for Service V2 |
| `enableConversationMonitoring` | Conversation monitoring |
| `enableAgentSneakPeek` | Agent sneak peek |
| `enableClientSneakPeek` | Customer sneak peek |
| `enableWhisperMessaging` | Whisper messaging |
| `enableSkillsAndQueueActions` | Queues and skills actions |

The V2 preference is Metadata API writable only when the target release contains that contract and the `OmniChannel.commandCenterForServiceV2Available` access check passes. That access check requires the feature gater and Enhanced Omni-Channel. Standard Omni orgs on the EOL extension cannot enable V2.

## ON-transition side effects

Changing `enableCommandCenterForServiceV2` from false to true invokes the existing `CommandCenterForServiceV2OrgPreference` hook. The hook:

1. inserts missing profile tab configurations for the V2 tab;
2. checks for `FlexiPage.DeveloperName='CommandCenterForServiceV2_L'`;
3. clones the platform seed only when that page is absent.

Disabling the preference does not delete the page. Re-enabling preserves an existing page. This skill enables but does not disable V2.

## Verification signals

The writer verifies the settings by a fresh Metadata API retrieve and verifies provisioning through:

```sql
SELECT Id FROM FlexiPage WHERE DeveloperName='CommandCenterForServiceV2_L'
```

using Tooling API, and:

```sql
SELECT Name FROM TabDefinition WHERE Name='standard-commandcenterforservicev2'
```

using the data API. Query errors remain `unknown` and block a successful write claim.

## User access

The org preference and its seed artifacts establish org-level readiness only. A supervisor also needs a permission set with `PermissionsCommandCenterForServiceUser=true`. This skill reports that follow-up but does not create users or permission sets.

## Whole-document requirement

Salesforce Settings metadata is deployed as a complete document. The implementation retrieves the current document and updates it in place. Do not replace this approach with a static template: a static template can silently drop existing Omni settings that are outside this skill's scope.
