# Data Mapper Completion Templates

Use these templates in Phase 3 (scoring output) and Phase 5 (completion summary).

## Scoring Output (Phase 3)

```
Score: XX/100 Rating
|- Design & Naming: XX/20
|- Field Mapping: XX/25
|- Data Integrity: XX/25
|- Performance: XX/15
|- Documentation: XX/15
```

**Thresholds**: ✅ 90+ (Deploy) | ⚠️ 67-89 (Review) | ❌ <67 (Block — fix required)

## Completion Summary (Phase 5)

```
Data Mapper Complete: [Name]
  Type: [Extract|Transform|Load|Turbo Extract]
  Target Object(s): [Object1, Object2]
  Field Count: [N mapped fields]
  Validation: PASSED (Score: XX/100)

Next Steps: Test in Integration Procedure, verify data output, monitor performance
```
