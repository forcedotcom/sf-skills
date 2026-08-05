# Wildcard Allowlist for `<members>*</members>`

This reference enumerates which Salesforce metadata types accept the wildcard member (`*`) inside a `package.xml` manifest, and which require explicit enumeration.

When in doubt, **enumerate explicitly**. The `sf project generate manifest --source-dir` and `--metadata` paths never emit `*`, which is the safest default.

---

## Wildcard ALLOWED

These types accept `<members>*</members>` and are commonly used that way in real projects. Each `*` matches every component of the type that the running user can see in the org (or every file on disk for source-dir builds).

| Metadata Type | Notes |
|---|---|
| `ApexClass` | All Apex classes (excluding managed package classes) |
| `ApexTrigger` | All Apex triggers |
| `ApexComponent` | All Visualforce components |
| `ApexPage` | All Visualforce pages |
| `AuraDefinitionBundle` | All Aura bundles |
| `LightningComponentBundle` | All LWC bundles |
| `StaticResource` | All static resources |
| `CustomApplication` | All custom apps |
| `CustomTab` | All custom tabs |
| `CustomMetadata` | Custom metadata records (use `Type.Record` notation if enumerating) |
| `Flow` | All flows; pair with explicit activation per `platform-metadata-deploy` |
| `FlexiPage` | All Lightning pages |
| `EmailTemplate` | All email templates the user can read |
| `Report` | All reports the user can read; folder-scoped |
| `Dashboard` | All dashboards the user can read; folder-scoped |
| `Document` | All documents in the user's accessible folders |
| `HomePageComponent` | All home page components |
| `HomePageLayout` | All home page layouts |
| `Letterhead` | All letterheads |
| `Queue` | All queues |
| `Group` | All public groups |
| `Role` | All roles |
| `Translations` | Per-locale translation files |
| `GlobalValueSet` | All global value sets |
| `GlobalValueSetTranslation` | All global value set translations |
| `Certificate` | All certificates |
| `ConnectedApp` | All connected apps |
| `RemoteSiteSetting` | All remote site settings |
| `NamedCredential` | All named credentials |
| `AuthProvider` | All auth providers |

---

## Wildcard NOT ALLOWED — Enumerate Explicitly

These types reject `*` outright OR silently produce broken manifests. Always list members explicitly.

| Metadata Type | Reason |
|---|---|
| `Profile` | Wildcard expansion includes standard profiles you almost certainly don't want to overwrite; the API rejects `*` for `Profile`. |
| `PermissionSet` | Same hazard as `Profile`. Enumerate the sets you actually own. |
| `PermissionSetGroup` | Enumerate explicitly. |
| `CustomLabels` | Container type; deploy the file as a unit, or list individual `CustomLabel` members. |
| `CustomObjectTranslation` | Locale-bound; must enumerate. |
| `Layout` | Layouts are object-bound (`Object-Layout Name`) and not wildcard-eligible. |
| `Workflow` | In some package configurations the API rejects `*`. Prefer enumerating object names. |
| `SharingRules` | Object-bound; enumerate. |
| `StandardValueSet` | Pre-defined platform list; must enumerate. |
| `ManagedTopics` | Site/community-bound; enumerate. |
| `CustomField` | Object-bound (`Object.Field`); not wildcard-eligible. |
| `RecordType` | Object-bound (`Object.RecordType`). |
| `BusinessProcess` | Object-bound. |
| `ListView` | Object-bound. |
| `ValidationRule` | Object-bound. |
| `WebLink` | Object-bound. |
| `CompactLayout` | Object-bound. |
| `FieldSet` | Object-bound. |
| `SharingReason` | Object-bound. |
| `SharingRecalculation` | Object-bound. |

---

## Special Cases

### Folder-scoped types

`Report`, `Dashboard`, `Document`, `EmailTemplate` accept `*`, but the wildcard only matches components in folders the running user can see. To include items in private folders, list folder names explicitly:

```xml
<types>
    <members>unfiled$public</members>
    <members>MyTeamReports</members>
    <name>ReportFolder</name>
</types>
<types>
    <members>*</members>
    <name>Report</name>
</types>
```

### Object-bound member syntax

For object-bound types, `<members>` uses `Object.ChildName` notation:

```xml
<types>
    <members>Account.Status__c</members>
    <name>CustomField</name>
</types>
<types>
    <members>Account.MyLayout</members>
    <name>Layout</name>
</types>
```

A `*` for the parent object does **not** transitively wildcard the children. Each object-bound child must be enumerated.

### `CustomObject` wildcard caveat

`<members>*</members>` for `CustomObject` matches custom objects only — not standard objects, not BigObjects, not external objects. To include `Account` or `Contact`, list them explicitly:

```xml
<types>
    <members>*</members>
    <members>Account</members>
    <members>Contact</members>
    <name>CustomObject</name>
</types>
```

---

## Verification

If a deploy fails with `Wildcards are not supported for this metadata type`, the manifest contains a `*` for a type in the "NOT allowed" table above. Replace it with an enumerated list and re-deploy.

The CLI path (`sf project generate manifest --source-dir` or `--metadata`) avoids this failure mode entirely because it never emits `*`.
