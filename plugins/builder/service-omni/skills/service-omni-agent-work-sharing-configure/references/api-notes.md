# AgentWork sharing API notes

## Supported contract

`AgentWork` is a standard object whose organization-wide defaults round-trip through the `CustomObject` Metadata API representation:

```xml
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <externalSharingModel>Private</externalSharingModel>
    <sharingModel>Read</sharingModel>
</CustomObject>
```

Retrieve with `CustomObject:AgentWork`. A deployment must preserve the retrieved `externalSharingModel`; only the internal `sharingModel` is changed.

## Access semantics

- `Private`: object permissions alone do not make every AgentWork record readable.
- `Read`: Public Read Only for internal access.
- `ReadWrite`: already includes read access, so this skill leaves it unchanged instead of narrowing access.

Object permissions, supervisor permissions, and supervisor configuration filters still apply. An OWD change does not grant object permission and does not select which reps appear in Command Center.

## Verification

A successful deploy response is insufficient. Retrieve `CustomObject:AgentWork` again and require:

- `sharingModel=Read` after a change.
- `externalSharingModel` equal to its pre-deploy value.

After metadata verification, sign in as the intended supervisor and validate that the expected work is visible and unrelated supervisor scopes remain filtered correctly.
