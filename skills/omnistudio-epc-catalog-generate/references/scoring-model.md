# EPC Bundle Scoring Model (120 Points)

Use this rubric when scoring or reviewing an existing EPC offer bundle. Score each category and sum for a total out of 120.

**Thresholds**: `>= 95` Deploy-ready | `70–94` Needs review | `< 70` Block and fix.

---

## 1) Catalog Identity and Naming (20 points)

- Product name is clear, unique, and follows naming conventions
- `ProductCode` follows the deterministic convention (no environment suffixes)
- `SpecificationType`, `SpecificationSubType`, and `Family` values are coherent
- Stable keying: `GlobalKey` is a UUID-style value; source key is consistent across files

---

## 2) EPC Product Structure (20 points)

- All required `Product2` and EPC fields are present and populated
- Lifecycle dates (`EffectiveDate`, `SellingStartDate`) are set and logically ordered
- `IsActive` and `%vlocity_namespace%__IsOrderable__c` flags are coherent with lifecycle status
- Record type and catalog classification are consistent

---

## 3) Attribute Modeling (25 points)

- Attributes are logically grouped by category
- Every attribute default exists within its `values[]` array
- Required, read-only, and filterable semantics are correctly set
- Display sequences are unique within each category and use spaced values (10, 20, 30…)

---

## 4) Offer Bundle Composition (25 points)

- Root `%vlocity_namespace%__ProductChildItem__c` row is present with `IsRootProductChildItem=true`
- All child product references are valid and their sequence/line numbers are unique
- `MinQuantity`, `MaxQuantity`, and default `Quantity` constraints are set correctly per child
- Optional vs required semantics are reflected accurately in min/max/default values

---

## 5) DataPack Integrity (15 points)

- All namespace placeholders (`%vlocity_namespace%`) are consistent across every file in the bundle
- Lookup object references use GlobalKey / source key (no hardcoded org-specific IDs)
- No environment-specific brittle fields (no `_DEV`, `_UAT`, `_PROD` suffixes in ProductCode or keys)

---

## 6) Documentation and Handoff (15 points)

- Clear explanation of the modeled intent is included in the handoff block
- Testing checklist is present (see `scripts/cli-validation-commands.sh`)
- Risks and assumptions are explicitly called out in the completion block
