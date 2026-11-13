# Metrics and Gauges

## Metric (KPI tile)

```xml
<dashboardComponent>
    <autoselectColumnsFromReport>false</autoselectColumnsFromReport>
    <chartSummary>
        <aggregate>Sum</aggregate>
        <column>AMOUNT</column>
    </chartSummary>
    <componentType>Metric</componentType>
    <decimalPrecision>-1</decimalPrecision>
    <displayUnits>Auto</displayUnits>
    <footer>Closed this financial year</footer>
    <groupingSortProperties/>
    <header>Income</header>
    <indicatorBreakpoint1>100000.0</indicatorBreakpoint1>
    <indicatorBreakpoint2>250000.0</indicatorBreakpoint2>
    <indicatorHighColor>#00716B</indicatorHighColor>
    <indicatorLowColor>#C23934</indicatorLowColor>
    <indicatorMiddleColor>#FFB75D</indicatorMiddleColor>
    <report>Sales_Reports/Closed_Won_This_FY</report>
    <showRange>true</showRange>
</dashboardComponent>
```

- The number is the report's **grand total** for the summary. No `groupingColumn`.
- All three `indicator*Color` elements are **required** ("Metric, gauge, or table dashboard component
  missing indicatorLowColor attribute").
- The number is drawn in the colour of its range: below `indicatorBreakpoint1` = low, between = middle,
  above `indicatorBreakpoint2` = high. **With no breakpoints the whole scale is "low"**, so the number
  shows in the low colour (red by default). For a neutral KPI set all three colours to the same value
  (e.g. `#181818` or a brand colour) and omit the breakpoints.
- `showRange` adds the range label under the number (e.g. "≥ 2M").
- `metricLabel` shows a second line under the header.
- `RowCount` and formulas: omit `<aggregate>`. Averages: `<aggregate>Average</aggregate>`.
- SLDS defaults the editor uses: low `#C23934`, middle `#FFB75D` (or `#CA8501`), high `#00716B`.

## Gauge

```xml
<dashboardComponent>
    <autoselectColumnsFromReport>false</autoselectColumnsFromReport>
    <chartSummary>
        <aggregate>Sum</aggregate>
        <axisBinding>y</axisBinding>
        <column>AMOUNT</column>
    </chartSummary>
    <componentType>Gauge</componentType>
    <decimalPrecision>-1</decimalPrecision>
    <displayUnits>Auto</displayUnits>
    <gaugeMax>3000000.0</gaugeMax>
    <gaugeMin>0.0</gaugeMin>
    <groupingSortProperties/>
    <header>Progress to 3M target</header>
    <indicatorBreakpoint1>1000000.0</indicatorBreakpoint1>
    <indicatorBreakpoint2>2000000.0</indicatorBreakpoint2>
    <indicatorHighColor>#00716B</indicatorHighColor>
    <indicatorLowColor>#C23934</indicatorLowColor>
    <indicatorMiddleColor>#FFB75D</indicatorMiddleColor>
    <report>Sales_Reports/Closed_Won_This_FY</report>
    <showPercentage>true</showPercentage>
    <showRange>true</showRange>
    <showTotal>true</showTotal>
    <showValues>false</showValues>
</dashboardComponent>
```

- `gaugeMin` / `gaugeMax` set the scale; breakpoints split it into three coloured segments.
- `showPercentage` shows the value as a % of `gaugeMax`; `showTotal` shows the value itself.
- Always set `gaugeMax`. (A gauge without it deploys; the scale is then undefined.)

## Dynamic gauge target (target from a record field)

Editor-built dynamic gauges carry:

```xml
<dashboardDynamicValues>
    <additionalInfo>{"target":"ENTITY_FIELD","footerMessage":"Sum of Amount compared to Target (Campaign: Annual Fund)"}</additionalInfo>
    <fieldName>Target_Amount__c</fieldName>
    <isDynamicUser>false</isDynamicUser>
</dashboardDynamicValues>
```

- `fieldName` is the field holding the target; `isDynamicUser` `true` takes it from the viewing/running
  user (e.g. a quota field on User).
<!-- TODO(verify in editor): how the target record is chosen for ENTITY_FIELD; the isDynamicUser=true XML. -->
