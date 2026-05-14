# TRANSCRIPT: VlocityOpenInterface → System.Callable Conversion

## Task

Convert `MyCustomVlocityOpenInterface2.cls` (VlocityOpenInterface) to System.Callable and create a test class. Keep a transcript of reasoning and skills used.

---

## Skills Used

| Skill | Purpose |
|-------|---------|
| **building-omnistudio-callable-apex** | Migration pattern, response envelope, action dispatch, inputMap/options contract, test patterns |
| **generating-apex** (implicit) | ApexDoc, type coercion, null safety, exception handling |

---

## Reasoning

### 1. Source Analysis

**Original class**: `MyCustomClass` implements `vlocity_cmt.VlocityOpenInterface`

- **Action**: `calculateTotal`
- **Inputs**: `Price` (Decimal), `Quantity` (Integer) from `inputs` map
- **Output**: Mutates `output` map with `TotalAmount`
- **Observation**: Original returns `true` for all method names (no unsupported-action handling)

### 2. Design Decisions

| Decision | Rationale |
|----------|------------|
| **Open Interface–compatible args** | Use `inputMap` and `options` keys per skill Phase 3 so OmniScript/IP callers can pass the same structure |
| **Flat args fallback** | Skill allows flat args when `inputMap` is absent; supports both calling styles |
| **Response envelope** | Return `{ success, data, errors }` instead of mutating `outputMap` per migration guidance |
| **Input validation** | Skill requires null-safe type coercion; OmniScript can send numbers as String |
| **Unsupported action** | Skill: use `switch on action` and throw `IndustriesCallableException` |
| **`with sharing`** | Skill guardrail: enforce sharing on callable classes |

### 3. Implementation Pattern

- **Entry point**: Extract `inputMap` and `options` from `args` (or treat flat `args` as `inputMap`)
- **Action dispatch**: `switch on action` with `when 'calculateTotal'` and `when else` throwing
- **Business logic**: `calculateTotal(inputMap, options)` returns envelope
- **Type coercion**: `toDecimal()` and `toInteger()` handle Decimal, Integer, Long, String (OmniScript casts)
- **Error envelope**: Missing/invalid inputs → `success: false` with `INVALID_INPUT` error code

### 4. Test Coverage (Phase 4)

| Test | Category | Purpose |
|------|----------|---------|
| `testCalculateTotal_Success` | Positive | InputMap/options format, validates TotalAmount |
| `testCalculateTotal_FlatArgs_Success` | Positive | Flat args backward compatibility |
| `testCalculateTotal_StringInputs_Success` | Contract | String coercion from OmniScript |
| `testUnsupportedAction_Throws` | Negative | Unsupported action throws `IndustriesCallableException` |
| `testCalculateTotal_MissingPrice_ReturnsError` | Contract | Missing required key returns error envelope |
| `testCalculateTotal_NullArgs_ReturnsError` | Contract | Null args handled without NPE |

### 5. Files Produced

| File | Role |
|------|------|
| `MyCustomCallable.cls` | Converted System.Callable |
| `MyCustomCallableTest.cls` | Test class |
| `IndustriesCallableException.cls` | Custom exception (skill pattern) |
| `TRANSCRIPT.md` | This transcript |

---

## Skill References

- **Phase 2 (Design)**: Contract mapping (`methodName`→`action`, `inputMap`/`options`→`args`)
- **Phase 3 (Implementation)**: Callable skeleton (inputMap/options), implementation rules (validate early, null-safe)
- **Phase 4 (Testing)**: Positive, negative, contract tests
- **Migration**: Preserve action names, return envelope instead of mutating output
