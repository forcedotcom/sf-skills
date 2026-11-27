# DML declarations (`InvocableActionExtension` sidecar)

If every successful invoke **always** inserts, updates or deletes records,
also generate an `InvocableActionExtension` sidecar declaring that DML.
Flow's Validation Exception Checker then treats the action like a Record
Insert/Update/Delete element and can warn about likely validation-rule
failures. The file is optional, and nothing checks it (honor system), so it
must be accurate.

- **Template:** `../assets/invocable-action-extension.invocableactionextension-meta.xml`
- **Path:** `force-app/main/default/invocableactionextensions/{ClassName}.invocableactionextension-meta.xml`.
  The file name and `<targetName>` must both equal the class name.
  `<targetType>ActionDefinition</targetType>`.
- **Versions:** the class's own `apiVersion` doesn't matter. The deploy
  (package/`sourceApiVersion`) must be 64.0+, because that's when
  `InvocableActionExtension` was added. The `DmlDeclarations` key also needs
  an org on a release that supports it. Older orgs reject it with *"The
  "DmlDeclarations" attribute key is invalid…"*. If that happens, drop the
  sidecar rather than renaming the key to `__c`.
- **Attribute:** `<key>DmlDeclarations</key>`, `<dataType>String</dataType>`,
  and a `<value>` holding a **JSON list** with one entry per operation and
  object.

**When to declare**

| The method… | Sidecar entry? |
|---|---|
| Always inserts/updates/deletes on every successful request | **Yes** |
| Does DML only on some branch (input flag, "if not found", "only if changed") | **No**, leave that operation out |
| Does no DML, or only does callouts or sends email | **No**. Don't generate the file. |
| Uses `Database.upsert` | Declare the operation it always resolves to. If it can be either insert or update, declare neither (there's no `UPSERT`). |

**Entry rules**

- Each entry has `operation` (`INSERT`, `UPDATE` or `DELETE`) and **exactly
  one** target:
  - `"object":"Case"` for a fixed object.
  - `"dynamicTypeRef":"T__records"` when the `@InvocableVariable` is a generic
    `SObject`/`List<SObject>`. The placeholder is `T__` plus the variable name.
  - `"isDynamicTarget":true` when the object comes from a runtime input,
    such as a String `objectApiName`.
- Add `"fields":[...]` with the field API names you write. If you leave it
  out, Flow assumes every field may be written.
- Deploy rejects an invalid value with *"The DML declarations value is
  invalid: …"*. For example, an entry that sets both `object` and
  `isDynamicTarget` fails with *"…must set exactly one of object,
  dynamicTypeRef or isDynamicTarget"*.

**Worked example: single object.** A method that always inserts one Case
per request:

```xml
<value>[{"operation":"INSERT","object":"Case","fields":["Subject","Description","Origin","ContactId"]}]</value>
```

**Multi-object example: Convert Lead.** A method that always converts with
`Database.convertLead` and always creates a new Account, Contact and
Opportunity:

```xml
<value>[{"operation":"INSERT","object":"Account","fields":["Name"]},{"operation":"INSERT","object":"Contact","fields":["FirstName","LastName","AccountId"]},{"operation":"INSERT","object":"Opportunity","fields":["Name","AccountId","StageName","CloseDate"]},{"operation":"UPDATE","object":"Lead","fields":["IsConverted","Status","ConvertedAccountId","ConvertedContactId","ConvertedOpportunityId"]}]</value>
```

If the request can pass an existing `accountId`, or sets
`setDoNotCreateOpportunity(true)`, those INSERT entries become conditional
and **must** be removed. The Lead UPDATE always stays.

Add the sidecar to `package.xml` / the deploy manifest as type
`InvocableActionExtension`, with member `{ClassName}`.
