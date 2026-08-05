# Metadata API Approach for Updating OWD

When the Tooling API approach is not suitable or the user prefers a metadata-driven workflow, use the Metadata API to update Organization-Wide Defaults.

## Step-by-Step Procedure

### 1. Create a project directory (if not already in an SFDX project)

```bash
sf project generate --name owd-update --template empty
cd owd-update
```

### 2. Retrieve the object metadata

Both standard and custom objects store their OWD sharing model in `<Object>.object-meta.xml` using the `<sharingModel>` and `<externalSharingModel>` elements.

```bash
sf project retrieve start --metadata CustomObject:<ObjectName> --target-org <org>
```

This creates a file at: `force-app/main/default/objects/<ObjectName>/<ObjectName>.object-meta.xml`

### 3. Locate the sharing model entries

The object metadata file contains `<sharingModel>` and `<externalSharingModel>` elements:

Example for a standard object (Account):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingModel>ReadWrite</sharingModel>
    <externalSharingModel>Private</externalSharingModel>
</CustomObject>
```

Example for a custom object (Invoice__c):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Invoice</label>
    <sharingModel>Private</sharingModel>
    <externalSharingModel>Private</externalSharingModel>
</CustomObject>
```

### 4. Modify the sharing model values

Update the `<sharingModel>` (internal access) and/or `<externalSharingModel>` (external access) to the desired access level. See `access_levels.md` for valid values per object.

### 5. Deploy the changes

```bash
sf project deploy start --metadata CustomObject:<ObjectName> --target-org <org>
```

### 6. Verify

Re-query using the Tooling API to confirm the change took effect:
```bash
sf data query --query "SELECT QualifiedApiName, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE QualifiedApiName = '<ObjectName>'" --use-tooling-api --target-org <org>
```

## When to Use This Approach

- User wants a source-trackable, version-controlled change
- Multiple OWD changes need to be deployed together
- Change is part of a larger metadata deployment
- Tooling API direct update is not permitted by org policies
