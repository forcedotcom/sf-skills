# Primitive Types & Constraints

Reference for all supported Lightning primitive types and their allowed constraints.

## Supported Types

- `lightning__textType`
  - Max length 255
- `lightning__multilineTextType`
  - Max length 2000
- `lightning__richTextType`
  - Max length 100000
- `lightning__urlType`
  - Max length 2000
  - Optional `lightning:allowedUrlSchemes` enum values: `https`, `http`, `relative`, `mailto`, `tel`
- `lightning__dateType`
  - Data pattern: YYYY-MM-DD
- `lightning__timeType`
  - Data pattern: HH:MM:SS.sssZ
- `lightning__dateTimeType`
  - Data shape is an object with required `dateTime` and optional `timeZone`
- `lightning__numberType`
  - Decimal numbers; optional `maximum`, `minimum`, `multipleOf`
- `lightning__integerType`
  - Whole numbers only; optional `maximum`, `minimum`
- `lightning__booleanType`
  - true/false

## Allowed Property-Level Keywords

When strict validation is enabled (`unevaluatedProperties: false`), keep each property minimal and prefer only keywords known to be allowed:

- `title`, `description`, `einstein:description`
- `type` (when used, ensure it matches the chosen `lightning:type`)
- `lightning:type`
- `maximum`, `minimum`, `multipleOf` (numeric)
- `maxLength`, `minLength` (string)
- `const`, `enum`
- `lightning:textIndexed`, `lightning:supportsPersonalization`, `lightning:localizable`
- `lightning:uiOptions`, `lightning:allowedUrlSchemes`
- `lightning:tags` (metaschema restricts values; currently `flow` is the only known allowed tag)
