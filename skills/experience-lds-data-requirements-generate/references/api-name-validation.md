# API Name Validation for Salesforce Objects and Fields

Validate every Salesforce API name reference in the LWC source before producing LDS code. For each reference, produce a `VERIFIED`, `UNVERIFIED`, or `AMBIGUOUS` entry per the output contract below.

## References that require validation

- **Unconfirmed object API names**: references to objects that may be custom or incorrectly named.
- **Ambiguous field references**: generic field names that map to multiple API names (e.g., "phone" → `Phone` vs `MobilePhone` vs `HomePhone`).
- **Suspected custom objects**: industry-specific terms or non-standard object references that likely end in `__c`.
- **Suspected custom fields**: field references that don't match standard Salesforce patterns.
- **Case-sensitivity issues**: API names that may have incorrect capitalization.
- **Missing `__c` suffixes**: custom objects/fields missing the required suffix.

## References that auto-validate

- Confirmed standard Salesforce objects (`Account`, `Contact`, `Lead`, `Opportunity`, `Case`, etc.) with exact casing.
- Confirmed standard fields with correct API names per the precision mapping below.
- Non-Salesforce data references.

## Validation Framework (Precision Mode)

**High-confidence object validation**

Standard Salesforce objects proceed with immediate validation confidence: `Account`, `Contact`, `Lead`, `Opportunity`, `Case`, `User`, `Task`, `Event`, `Product2`, `Pricebook2`, `Order`, `OrderItem`, `Asset`, `Contract`, `Campaign`.

Any deviation from exact standard naming triggers verification.

**Custom object detection and verification**

- Industry-specific terminology (e.g., `Gym`, `Property`, `Course`, `Equipment`) indicates potential custom objects.
- Non-standard object references require explicit API name confirmation.
- Objects with a `__c` suffix need org-specific verification of exact naming.
- Never assume custom object API names — always require explicit confirmation.

**Standard field precision mapping**

- `Account`: `Name`, `Phone`, `Website`, `BillingAddress`, `ShippingAddress`, `Industry`, `Type`, `Description`.
- `Contact`: `FirstName`, `LastName`, `Name`, `Email`, `Phone`, `MobilePhone`, `MailingAddress`, `Department`, `Title`.
- `Opportunity`: `Name`, `StageName`, `CloseDate`, `Amount`, `Probability`, `AccountId`, `Type`.
- `Case`: `Subject`, `Status`, `Priority`, `Origin`, `Description`, `ContactId`, `AccountId`.

**Field ambiguity resolution patterns**

- Generic "phone" → require confirmation: `Phone`, `MobilePhone`, `HomePhone`, `OtherPhone`, or `WorkPhone`.
- Generic "address" → require confirmation: `BillingAddress`, `ShippingAddress`, `MailingAddress`, or `OtherAddress`.
- Generic "name" → require confirmation: `Name` (full), `FirstName`, `LastName`, or `CompanyName` depending on object.
- Generic "status" → require confirmation: `Status`, `StageName`, or custom status field API name.

**Custom field identification criteria**

- Field names not matching standard Salesforce patterns for the object type.
- Technical or business-specific jargon.
- Fields missing the required `__c` suffix.
- Case-sensitivity violations in API name references.

## Output contract

For each API name reference in the source, produce one entry with these fields:

- **`reference`** — the object or field name as written in the source (e.g. `Account.Phone`, `Gym__c.Capacity__c`).
- **`status`** — exactly one of `VERIFIED`, `UNVERIFIED`, `AMBIGUOUS`.
- **`source`** — for `VERIFIED`, the source of truth consulted (e.g. "standard object — SObject describe", "FieldDefinition row for `Gym__c.Capacity__c`"). For `UNVERIFIED` or `AMBIGUOUS`, the missing input needed (e.g. "no SObject describe for `Gym__c` in target org", "ambiguous — caller must select between `Phone` and `MobilePhone`").
- **`resolution`** — the corrected API name with `__c` suffix, exact capitalization, and disambiguation applied. For `UNVERIFIED`, prefix with `UNVERIFIED:` followed by the best-guess name (e.g. `UNVERIFIED: Gym__c.Capacity__c`).

Do not emit TODO comments in the LWC code or PRD — the validation entry above is the production output. If every reference is `VERIFIED`, produce an empty list.
