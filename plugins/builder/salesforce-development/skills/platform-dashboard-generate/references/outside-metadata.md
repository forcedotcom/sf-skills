# Features the Dashboard File Cannot Carry

Tell the user plainly when a request needs one of these; do not invent XML for them.

| Feature | Where it lives | What metadata does |
|---------|----------------|--------------------|
| **Reference lines** (target line on a chart, Winter '26) | Builder only: Edit widget → Show Reference Line → value + colour | Not retrieved. An unchanged redeploy keeps them; **deploying a changed widget deletes its reference line silently**; they never move to another org. Before editing a dashboard that has them, list them, then re-add them in the builder after the deploy. |
| Email subscriptions / scheduled refresh | User's Subscribe button (daily/weekly/monthly; users, groups, roles; up to 500 recipients). Untick "Receive new results by email" for a refresh-only schedule | Not in the file. Not available for dynamic dashboards; recipients see the running user's data. |
| Single-widget refresh | Reports and Dashboards Settings | — |
| Translations of name, widget title/subtitle/footer | Translation Workbench | Not in the dashboard file |
| Following, Chatter posts, favourites, Collections | Runtime | — |
| Showing the dashboard on a Home / App page | Lightning App Builder "Dashboard" component | Use `platform-flexipage-generate`. Record pages use the Report Chart component instead. |
| Experience Cloud | Aura: Dashboard component; LWR: "Lightning Dashboard" component (beta, Winter '27, enable in Reports and Dashboards Settings) | Viewers need folder access and object read access. |
| Salesforce mobile app | Automatic, view-only; text, image and link widgets are not shown | — |
| Slack | Post to Slack / subscriptions (PNG snapshot) | — |

## Not Lightning dashboards

| Product | Metadata | Skill |
|---------|----------|-------|
| CRM Analytics dashboards | `WaveDashboard` | not this skill |
| Tableau Next dashboards | `AnalyticsDashboard` | not this skill |
| Tableau Cloud/Server views | Tableau View Lightning component on a page | `platform-flexipage-generate` |
