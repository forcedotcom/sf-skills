# Portal Creation Report — template

The skill's final action (Step 4) is always to write `report.md`. It must start with the heading
`# Portal Creation Report`, cover the portal name, the API used and why, the framework/template, the
dispatched request + response, the remaining Step 3 work, and end with the exact sentinel line
`Task completed: portal creation dispatched — see report.md`.

Skeleton:

```markdown
# Portal Creation Report

- **Portal name:** IT Support Portal
- **API:** POST /services/data/v67.0/connect/communities — chosen because no guest Embedded Service
  Deployment exists (self-service/site requires one).
- **Framework / template:** Aura — Agentforce Employee Center

## Dispatched
POST /services/data/v67.0/connect/communities
{ "name": "IT Support Portal", "urlPathPrefix": "itsupport", "templateName": "Agentforce Employee Center" }

## Response
{ "jobId": "08P...", "status": "Queued" }

## Remaining
- Step 3: Activate (Network status Live) → Add Members (profiles) → Publish (`sf community publish`).
- Embedded Agentforce agent is a separate follow-up step (not created by this call).

Task completed: portal creation dispatched — see report.md
```
