# LWC Template: Dashboard Card Mockup

## Prompt Template

```
Salesforce Lightning dashboard card/tile mockup:

CARD TYPE: [metric/chart/list/progress]

METRIC CARD:
- Large metric value
- Label below
- Trend indicator: up/down arrow with percentage
- Sparkline mini chart (optional)
- Icon in corner

CHART CARD:
- Chart type: [bar/line/pie/donut]
- Legend position
- Data labels on hover

LIST CARD:
- Title with "View All" link
- 3-5 list items
- Each item: icon, primary text, secondary text

STYLING:
- SLDS card component
- White background with subtle shadow
- Rounded corners
- Header with title and action menu
```

## Example: Metric Card

```bash
gemini "/generate 'Salesforce dashboard metric card:
- Large number: $1.2M
- Label: Total Pipeline Value
- Trend: +12% (green up arrow)
- Icon: Opportunity icon (top-right)
- Sparkline: Show 7-day trend mini chart

Style: SLDS card, white background, subtle shadow'"
```
