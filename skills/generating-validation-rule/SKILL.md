---
name: generating-validation-rule
description: Use this skill when users need to create, modify, or validate Salesforce Validation Rules. Trigger when users mention validation rules, field validation, data quality rules, formula validation, error messages, or validation logic. Also use when users encounter validation errors, need to update formulas, or want to enforce business rules at the data layer. Always use this skill for any validation rule work.
---

## When to Use This Skill

Use this skill when you need to:
- Create validation rules to enforce data quality
- Prevent invalid records from being saved
- Generate validation rule metadata with formulas
- Add business logic validation to objects
- Troubleshoot deployment errors related to validation rules

## Specification

# ValidationRule Metadata Specification

### 📋 Overview
Validation Rules are declarative metadata components used to enforce data quality and business logic in Salesforce. They evaluate a formula expression when a record is saved and prevent the save operation if the expression returns TRUE.

### 🎯 Purpose
-Enforce business rules at the data layer
-Prevent invalid or incomplete records from being saved
-Display meaningful error messages to guide users

### ⚙️ Required Properties

#### Core Validation Rule Properties

- **fullName**
    - The unique API name of the validation rule
    - Must start with a letter
        - Can contain letters, numbers, and underscores
    - Cannot end with an underscore
    - Cannot contain consecutive underscores
    - Cannot exceed 40 character.

- **active**
  -Indicates whether the validation rule is enabled
  true → Rule is enforced
  false → Rule is inactive

- **errorConditionFormula**
- The logical formula that evaluates record data
- Must return TRUE or FALSE
- If TRUE, the validation rule triggers an error

- **errorMessage**
    - The message displayed to the user when validation fails
- Maximum length: 255 characters

### Specific Function Guidelines
- TEXT - TEXT() function MUST NOT be used with Text fields, to fix this you can just remove the TEXT() function.
- CASE - In salesforce CASE() function, last parameter is the default value. Admins often miss to provide this and number of parameters to CASE() function are always even.
- VALUE - VALUE() function should only be used with Text fields. If a number is being used as a parameter to the VALUE() function, remove the VALUE() function.
- DAY - DAY() function should only be used with Date fields. If a Datetime field is being used as a parameter to the DAY() function, convert it into a Date first.
- MONTH - MONTH() function should only be used with Date fields. If a Datetime field is being used as a parameter to the MONTH() function, convert it into a Date first.
- DATEVALUE - DATEVALUE() function should only be used with DateTime fields. If a Date is being used as a parameter to the DATEVALUE() function, remove the DATEVALUE() function.
- ISPICKVAL - If checking equality of a picklist type field, the function ISPICKVAL() MUST be used.
- ISCHANGE - Use ISCHANGE() function to check the value of a record has changed.

### Critical Rules
1. Formula XML Handling(MOST COMMON ERROR)
    - ANY errorConditionFormula containing XML tags MUST be inside a CDATA section in the metadata XML.

2. Interpretation of "Update" Instructions. When receiving instructions to modify a formula, distinguish between a replacement and an addition:
    - "Update the formula to [Action]": Completely replace the existing formula logic with the new requirement.
    - "Update the formula to also [Action]": Keep the existing logic and append the new requirement (usually by wrapping the logic in an AND() or OR() function).

3. File Format Requirement
    - Validation rule files MUST always use the `.validationRule-meta.xml` extension.
