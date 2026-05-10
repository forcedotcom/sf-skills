# SFSQL Function Catalog — for `formula` reasoning

> **Last synced:** 2026-04-23 from the Data Processing Engine PDF (2025-06-24 version) and
> the BDT help DITA XMLs (`c360_a_batch_transform_numeric.xml`, `_string.xml`,
> `_date_functions.xml`, `_boolean_functions.xml`, `_multivalue_functions.xml`,
> `_additionalfunctions.xml`). Consult this file before interpreting any `formulaExpression`.

## How formulas appear in BDT JSON

```jsonc
"action": "formula",
"parameters": {
  "expressionType": "SQL",        // or "DCSQL"
  "fields": [
    {
      "name": "OutputField__c",
      "label": "Output Label",
      "type": "TEXT",             // TEXT | NUMBER | BOOLEAN | DATE_ONLY | DATETIME
      "businessType": "Text",     // user-visible type name
      "formulaExpression": "upper(coalesce(SourceField__c, ''))",
      "precision": 255,
      "scale": 0,                 // only for NUMBER
      "defaultValue": ""
    }
  ]
}
```

## Functions by family

### Math / Numeric

| Function | Signature | Purpose |
|---|---|---|
| `abs(n)` | number → number | Absolute value (strips sign). |
| `ceiling(n)` | number → number | Round up, away from zero for negatives. |
| `floor(n)` | number → number | Round toward negative infinity. Always rounds down on the number line: `floor(2.7) = 2`, `floor(-2.3) = -3`. |
| `exp(n)` | number → number | e raised to n. |
| `log(base, n)` | number → number | Logarithm of n in the given base. |
| `max(a, b, …)` | number → number | Largest value. |
| `min(a, b, …)` | number → number | Smallest value. |
| `mod(a, b)` | number → number | Remainder after dividing a by b. |
| `power(a, b)` | number → number | a raised to the power b. |
| `round(n, digits)` | number → number | Round to `digits` places. |
| `sqrt(n)` | number → number | Positive square root. |
| `trunc(n, digits)` | number → number | Truncate to `digits` places (doesn't round). |

### String

| Function | Signature | Purpose |
|---|---|---|
| `begins(s, prefix)` | text → boolean | True if s starts with prefix. |
| `concat(a, b, …)` | text → text | Concatenate. |
| `contains(haystack, needle)` | text → boolean | True if haystack contains needle. |
| `ends(s, suffix)` | text → boolean | True if s ends with suffix. |
| `length(s)` | text → number | Character count. |
| `lower(s)` | text → text | Lowercase (locale-aware if a locale is provided). |
| `ltrim(s)` / `ltrim(s, substring)` | text → text | Remove leading whitespace (or a specific substring). |
| `rtrim(s)` / `rtrim(s, substring)` | text → text | Remove trailing whitespace (or substring). |
| `substitute(s, old, new)` | text → text | Replace old with new in s. |
| `substr(s, start, length)` | text → text | Extract a substring. |
| `text(n)` | number → text | Convert a number to its text form. |
| `trim(s)` / `trim(s, substring)` | text → text | Remove leading + trailing whitespace or substring. |
| `upper(s)` | text → text | Uppercase. |
| `uuid()` | → text | Newly generated unique ID. |
| `value(s)` | text → number | Parse a text representation of a number into a numeric value. |

### Date

| Function | Signature | Purpose |
|---|---|---|
| `adddays(date, n)` | date → date | Add n days. |
| `addmonths(date, n)` | date → date | Add n months. |
| `datediff(start, end)` | date × date → number | Days between two dates. |
| `datetimevalue(text_or_date)` | → datetime | GMT/UTC date+time value. |
| `datevalue(text_or_datetime)` | → date | Extract the date part. |
| `day(date)` | date → number | 1-31. |
| `monthdiff(start, end)` | date × date → number | Months between two dates. |
| `now()` | → datetime | Current moment (UTC). |
| `today()` | → date | Current date. |
| `weekday(date)` | date → number | 1=Sunday, 2=Monday, … 7=Saturday. |

### Boolean / Logical

| Function | Signature | Purpose |
|---|---|---|
| `and(a, b, …)` | bool → bool | True when all are true. |
| `or(a, b, …)` | bool → bool | True when any is true. |
| `if(cond, then_val, else_val)` | → any | Ternary. |
| `case when <cond1> then <val1> else <elseval> end` | — | Multi-branch (SQL CASE). |
| `blankvalue(expr, substitute)` | → any | Substitute when expr is blank. |
| `isblank(expr)` | → bool | True when expr is blank. |
| `isnull(expr)` | → bool | True when expr is null. |
| `nullvalue(expr, substitute)` | → any | Substitute when expr is null; returns expr otherwise. |

### Multivalue

| Function | Signature | Purpose |
|---|---|---|
| `sequence(start, end, step?)` | → array | Array of numbers/dates between start and end (step defaults to 1 / 1 day). |
| `explode(array)` | → row per element | Convert multivalue data into one row per element. **Cannot be nested inside another function.** |

### Additional / Null-handling (commonly seen)

| Function | Signature | Purpose |
|---|---|---|
| `coalesce(a, b, …)` | → any | First non-null argument (SQL standard). |

## Patterns to recognize in narration

- **`coalesce(X, Y)`** — "use X when present, otherwise Y." Very common for default-value
  handling.
- **`case when RANK = 1 then X else 0 end`** — the "first-occurrence extract" idiom paired
  with a `computeRelative` `row_number()` node.
- **`case when FLAG = 'Y' then 'Y' else 'N' end`** — boolean-like text normalization.
- **`concat(coalesce(A, ''), coalesce(B, ''))`** — safe string concatenation that defaults
  NULLs to empty strings (producing a synthetic composite key).

## Sources

- Data Processing Engine reference PDF (captured at `research/bdt-doc-10-data_processing_engine_6-24-2025.pdf.md`)
- BDT help XML: `c360_a_batch_transform_numeric.xml`, `_string.xml`, `_date_functions.xml`,
  `_boolean_functions.xml`, `_multivalue_functions.xml`, `_additionalfunctions.xml` (captured
  at `research/help-xml/`).
