# Best Practices

Long-form rationale + examples for each principle summarized in [SKILL.md](../SKILL.md#best-practices).

## Prefer CLC Fields Over Raw Fields

When creating fields, prefer calculated fields (`_clc`) even for simple formulas. This centralizes business logic and makes it reusable.

**Example:**
```bash
# Instead of using raw [Table].[Amount] everywhere, create:
python scripts/create_calc_field.py \
  --sdm Sales_Cloud12_backward \
  --type measurement \
  --name Total_Revenue_clc \
  --label "Total Revenue" \
  --expression "SUM([Opportunity_TAB_Sales_Cloud].[Amount])" \
  --aggregation Sum
```

## Use Meaningful Names

API names should communicate business meaning, not generic identifiers.

**Good:**
- `Win_Rate_clc`
- `Total_Revenue_mtc`
- `Deal_Size_Category_clc`

**Bad:**
- `Field_1_clc`
- `Metric_2_mtc`
- `Calc_Field_clc`

## Two-Step Workflow for Metrics

Create the calculated field first, then the metric. Metrics reference calc fields by API name in `measurementReference.calculatedFieldApiName`, so attempting to create a metric before its calc field exists will fail with a "Field not found" error.

## Test Fields Before Creating Metrics

After creating a calc field, verify it works in a visualization before creating a metric. This catches expression errors early.

**Verification steps after field/metric creation:**
1. **Confirm existence:** Run `discover_sdm.py --sdm {{NAME}} --json` and search for your API name in the response
2. **Check API response:** POST response includes `apiName` and `success: true` on successful creation
3. **Test in visualization:** Create a simple chart using the calc field, or reference the metric in a dashboard widget
4. **Validate calculations:** Compare output values against manual calculations to verify expression logic

## Read Aggregation Types from SDM

Don't assume aggregation types — inspect the SDM to see how similar fields are configured. Use `discover_sdm.py --sdm {{NAME}} --json` and look at `aggregationType` for existing measurements.
