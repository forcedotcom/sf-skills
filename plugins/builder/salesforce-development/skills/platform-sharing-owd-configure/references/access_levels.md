# OWD Access Levels Reference

## Valid Access Level Values

| API Value | Display Name | Description |
|-----------|-------------|-------------|
| `Private` | Private | Only record owner and users above in role hierarchy can view/edit |
| `Read` | Public Read Only | All users can view records but only owner can edit |
| `ReadWrite` | Public Read/Write | All users can view and edit all records |
| `ReadWriteTransfer` | Public Read/Write/Transfer | All users can view, edit, and transfer ownership (Cases, Leads only) |
| `FullAccess` | Public Full Access | All users have full access including delete (Campaigns only) |
| `ControlledByParent` | Controlled by Parent | Access determined by parent record's sharing (requires Master-Detail) |

## Object-Specific Restrictions

| Object | Allowed Values | Notes |
|--------|---------------|-------|
| Account | Private, Read, ReadWrite | Contact and Opportunity OWD tied to Account when ControlledByParent |
| Contact | Private, Read, ReadWrite, ControlledByParent | ControlledByParent ties to Account |
| Opportunity | Private, Read, ReadWrite, ControlledByParent | ControlledByParent ties to Account |
| Case | Private, Read, ReadWrite, ReadWriteTransfer | Transfer is unique to Case |
| Lead | Private, Read, ReadWrite, ReadWriteTransfer | Transfer is unique to Lead |
| Campaign | Private, Read, ReadWrite, FullAccess | FullAccess is unique to Campaign |
| Custom Objects | Private, Read, ReadWrite, ControlledByParent | ControlledByParent requires Master-Detail field |

## Cross-Object Constraints

| Constraint | Detail |
|-----------|--------|
| Account = Private cascades | Setting Account to Private forces Contact, Case, and Opportunity to Private — all four recalculate together |
| Contract tied to Account | Contract OWD cannot be set independently; it follows Account's OWD |
| Pricebook | Only accepts `Use` or `No Access` (`ReadSelect` / `None` in API) — standard access levels do not apply |
| ControlledByParent cascade | If a child object uses ControlledByParent, changing the parent's OWD implicitly changes the child's effective access |

## Internal vs External Access

- **Internal access**: Applies to users within the org (internal users)
- **External access**: Applies to external users (Community/Experience Cloud users, portal users)
- External access can never be more permissive than internal access
- External OWD must be enabled in Setup before external values appear

## Common Transitions

| From | To | Impact |
|------|-----|--------|
| Public Read/Write → Private | High | Triggers full sharing recalculation; users lose access immediately |
| Private → Public Read Only | Medium | Grants read access to all; recalculation needed |
| Private → Public Read/Write | Low | Opens access broadly; fast operation |
| Any → ControlledByParent | High | Requires Master-Detail relationship; existing sharing rules deleted |
