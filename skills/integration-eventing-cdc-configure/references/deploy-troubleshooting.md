# CDC Deploy Troubleshooting

Errors observed during real org dry-runs while authoring this skill, with the metadata-side fix.

## "Unable to find the specified channel"

The `<eventChannel>` value doesn't match a channel known to the org.

- For the default channel, the value must be exactly `ChangeEvents`. NOT `data/ChangeEvents`, NOT `/data/ChangeEvents`, NOT `data/ChangeEvent`.
- For a custom channel, the value must match the channel's DeveloperName **including the `__chn` suffix** — e.g. `PartnerSync__chn`.
- If the custom channel is in the same deploy, ensure it's in the same package directory so MDAPI orders the deploy correctly.

## "...invalid event in the 'selectedEntity' field"

`<selectedEntity>` must be the ChangeEvent entity, not the source object.

| Source | Wrong | Right |
|---|---|---|
| `Account` | `Account` | `AccountChangeEvent` |
| `Lead` | `Lead` | `LeadChangeEvent` |
| `Order__c` | `Order__c` | `Order__ChangeEvent` |
| `Custom__c` | `Custom__c` | `Custom__ChangeEvent` |

For custom objects, swap the trailing `__c` for `__ChangeEvent` — the double underscore separator is preserved.

## "Cannot create a new component with the namespace: <Object>"

The member's fullName has two underscores between the entity and `ChangeEvent`. Salesforce parses `Foo__Bar` as `<namespace>__<name>` and rejects creation outside the org's own namespace.

- Member fullName format: `<Entity>_ChangeEvent` (single underscore).
- File name: `<Entity>_ChangeEvent.platformEventChannelMember-meta.xml`.

This applies even when the source object has `__c` — the member fullName drops the `__c` and uses single underscore: file `Order_ChangeEvent.platformEventChannelMember-meta.xml`, fullName `Order_ChangeEvent`.

## "The selected field, X.Y, isn't valid" (enrichedFields)

Enrichment fields must be **single-hop API names on the source entity**. Field type doesn't matter — standard lookup IDs, custom lookups, and custom non-relationship fields all work. The rejection is specifically for relationship-traversal syntax (`X.Y`, `__r.Y`).

Verified working in dry-run:

| Field | Type | Result |
|---|---|---|
| `OwnerId` | standard lookup ID | ✓ deploys |
| `ParentId` | standard lookup ID | ✓ deploys |
| `MyAccountManager__c` | custom Lookup → User | ✓ deploys |
| `Region__c` | custom Text | ✓ deploys |
| `Status__c` | custom Picklist | ✓ deploys |

Verified rejected:

| Field | Why |
|---|---|
| `Owner.Name` | relationship traversal |
| `Parent.Account.Industry` | multi-hop traversal |
| `MyLookup__r.Name` | relationship traversal (custom) |

When the user says "include the owner's name in every event," the metadata stores `OwnerId` — CDC enriches the lookup automatically and the consumer resolves the related record from the ID.

## "filter expression has syntax errors: unexpected token: 'WHERE'"

The body of `<filterExpression>` is a SOQL WHERE-clause body — without the `WHERE` keyword.

| Wrong | Right |
|---|---|
| `WHERE Status__c != null` | `Status__c != null` |
| `WHERE Industry IN ('Tech', 'Finance')` | `Industry IN ('Tech', 'Finance')` |

## ChangeEvent entity doesn't exist (for custom objects)

`Foo__ChangeEvent` only exists if `Foo__c` exists. If both are being deployed in the same dry-run, the dry-run validator may flag the member because it validates entity references against the *current* org state, not the post-deploy state. Mitigations:

- Deploy the source object first, then the channel member in a second deploy.
- Or accept that dry-run will flag this case but a real (non-dry-run) deploy succeeds because MDAPI orders the components correctly.
