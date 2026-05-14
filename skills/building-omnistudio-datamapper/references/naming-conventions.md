<!-- Parent: building-omnistudio-datamapper/SKILL.md -->

# Data Mapper Naming Conventions

## Type Prefixes

Every Data Mapper name starts with a type prefix that identifies its function at a glance.

| Type | Prefix | Example |
|------|--------|---------|
| Extract | `DR_Extract_` | `DR_Extract_Account_Details` |
| Turbo Extract | `DR_TurboExtract_` | `DR_TurboExtract_Case_List` |
| Transform | `DR_Transform_` | `DR_Transform_Lead_Flatten` |
| Load | `DR_Load_` | `DR_Load_Opportunity_Create` |

The `DR_` prefix stands for DataRaptor, the original product name. It remains the standard prefix for backward compatibility and team familiarity.

---

## Object Naming

### Format

```
DR_[Type]_[PrimaryObject]_[Purpose]
```

- **Type**: Extract, TurboExtract, Transform, Load
- **PrimaryObject**: The main Salesforce object (PascalCase, no underscores for standard objects)
- **Purpose**: A short, descriptive action or qualifier (PascalCase)

### Standard Object Examples

| Data Mapper | Description |
|-------------|-------------|
| `DR_Extract_Account_Details` | Extract Account fields for detail view |
| `DR_Extract_Account_WithContacts` | Extract Account with related Contact list |
| `DR_Extract_Contact_ByAccountId` | Extract Contacts filtered by Account |
| `DR_TurboExtract_Case_OpenList` | High-volume Extract of open Cases |
| `DR_Transform_Order_FlattenLines` | Flatten nested OrderItem structure |
| `DR_Load_Opportunity_Create` | Insert Opportunity records |
| `DR_Load_Account_Upsert` | Upsert Account records by external ID |

### Custom Object Examples

For custom objects, include the namespace prefix if applicable but drop the `__c` suffix from the name:

| Data Mapper | Target Object | Description |
|-------------|---------------|-------------|
| `DR_Extract_Invoice_Summary` | `Invoice__c` | Extract Invoice summary fields |
| `DR_TurboExtract_Claim_Active` | `Claim__c` | High-volume active Claims list |
| `DR_Load_PolicyHolder_Update` | `PolicyHolder__c` | Update PolicyHolder records |
| `DR_Extract_ns_CustomObj_Details` | `ns__CustomObj__c` | Namespaced custom object Extract |

### Multi-Object Data Mappers

When a Data Mapper spans multiple objects, name it after the primary (root) object:

```
DR_Extract_Account_WithContactsAndOpps
DR_Extract_Order_WithLineItems
```

If the Data Mapper truly serves a cross-cutting concern, use a domain name instead:

```
DR_Extract_CustomerProfile_Full
DR_Transform_ClaimSubmission_Normalize
```

---

## Field Mapping Naming Patterns

### Output Field Names

Output field names in the Data Mapper JSON response should follow these conventions:

| Pattern | Convention | Example |
|---------|-----------|---------|
| Standard fields | camelCase matching API name | `accountName`, `billingCity` |
| Custom fields | camelCase without `__c` suffix | `invoiceTotal` (from `Invoice_Total__c`) |
| Relationship fields | parent + field in camelCase | `accountOwnerName` (from `Account.Owner.Name`) |
| Child collections | plural camelCase | `contacts`, `orderItems` |
| Computed/aliased fields | descriptive camelCase | `fullAddress`, `daysSinceCreated` |

### Input Path Conventions

Input paths reference the source data structure. Use consistent dot notation:

```
AccountData.Name          -- Simple field
AccountData.Owner.Name    -- Relationship traversal
AccountData.Contacts[0]   -- Collection index
RequestBody.payload.id    -- Nested JSON path
```

### Output Path Conventions

Output paths define the JSON structure returned by the Data Mapper:

```
AccountInfo.Name           -- Nested output
AccountInfo.OwnerName      -- Flattened relationship
AccountInfo.Contacts       -- Collection output
Result.status              -- Top-level result wrapper
```

---

## Naming Anti-Patterns

| Anti-Pattern | Problem | Correct |
|--------------|---------|---------|
| `DataRaptor1` | Non-descriptive, no type prefix | `DR_Extract_Account_Details` |
| `GetAccountData` | Missing `DR_` prefix and type | `DR_Extract_Account_Details` |
| `DR_Extract_Account__c_Details` | Includes `__c` suffix | `DR_Extract_Account_Details` |
| `DR_extract_account_details` | Wrong casing (should be PascalCase) | `DR_Extract_Account_Details` |
| `DR_Extract_Everything` | Too vague, no object specified | `DR_Extract_Account_Full` |
| `DR_Extract_AccountDetailsForTheNewCustomerPortalPage` | Too long | `DR_Extract_Account_PortalDetails` |
| `DR_Extract_Acc_Det` | Abbreviations reduce readability | `DR_Extract_Account_Details` |

---

## Version and Environment Conventions

Data Mapper names should be environment-agnostic. Do not include environment identifiers in the name:

```
Bad:   DR_Extract_Account_Details_DEV
Bad:   DR_Extract_Account_Details_v2
Good:  DR_Extract_Account_Details
```

Use OmniStudio versioning (built into the platform) to manage iterations. The Data Mapper name stays constant across environments and versions.

---

## Character Limits and Restrictions

- Maximum name length: 80 characters
- Allowed characters: letters, numbers, underscores
- Must start with `DR_`
- No spaces, hyphens, or special characters
- PascalCase after each underscore delimiter
