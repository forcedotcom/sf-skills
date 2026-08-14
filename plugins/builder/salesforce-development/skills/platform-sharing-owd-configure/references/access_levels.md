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
| Pricebook2 (Price Book) | Internal: ReadSelect (Use), Read (View Only), None (No Access) | **External is fixed at `None` — immutable, cannot be changed** |
| Custom Objects | Private, Read, ReadWrite, ControlledByParent | ControlledByParent requires Master-Detail field |

## Cross-Object Constraints

| Constraint | Detail |
|-----------|--------|
| Account = Private cascades | Setting Account to Private forces Contact, Case, and Opportunity to Private — all four recalculate together |
| Contract tied to Account | Contract OWD cannot be set independently; it follows Account's OWD |
| Pricebook (internal) | Only accepts `Use`, `View Only`, or `No Access` (`ReadSelect` / `Read` / `None` in API) — standard access levels do not apply |
| Pricebook (external) | **Fixed at `None` (No Access) — immutable, cannot be changed via Metadata API, Tooling API, or Setup UI** |
| ControlledByParent cascade | If a child object uses ControlledByParent, changing the parent's OWD implicitly changes the child's effective access |

## Immutable / Fixed OWD Objects

Some objects have OWD values that are platform-fixed and **cannot be changed by any means** (Metadata API, Tooling API, or Setup UI). Attempting to deploy a change will always fail. If the user requests a change to one of these, **explain upfront that it is not possible** — do not attempt a deploy.

| Object | Field | Fixed Value | Notes |
|--------|-------|-------------|-------|
| Pricebook2 (Price Book) | External OWD | `None` (No Access) | Platform-enforced; only internal OWD (`Use`/`View Only`/`No Access`) is configurable |
| User | Internal & External | Read | Cannot be changed |
| Activity (Task/Event) | External | Private | Only internal OWD is configurable via "Activity" settings |
| Knowledge Article | External | Controlled by separate channel visibility | Not configurable as a standard OWD |

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
