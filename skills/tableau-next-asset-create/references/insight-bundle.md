# Insight bundle and metric render — app-only payloads

Cited from `tasks/build-dashboard.md` and `dashboard-authoring.md`. **Not a
first hop. Not a user dispatch.** Do not call these because a chat user said
"generate insights."

The MCP tools are namespaced per server — names here are bare; use whichever
server prefix is connected.

---

## `generate_insight_bundle`

Produces a Tableau Next insight bundle (live value, trend, and status) for a
**dashboard metric widget**.

**Internal / app-only.** `visibility=app` hides it from the model's tool
list. Intended for the MCP app renderer via `app.callServerTool()`, **not**
for the model to invoke on a user chat turn.

The renderer forwards the metric definition it already holds. The server
delegates to the internal insights service via a named-credential callout;
the org JWT is **minted server-side**. Do **not** mint or pass a browser JWT.

Access also requires permission to view Tableau dashboards (plus the Analytics
family's org-level Tableau / semantic-layer check).

### Body (opaque JSON, forwarded verbatim)

Connect does not reshape the body. Field set tracks
`GenerateInsightBundleRequest`:

- `input` — metric bundle input (metric reference + evaluation context:
  measurement/metric, grain, filters, time range the widget is showing)
- `options` — which artifacts to compute (value, trend/comparison,
  status/threshold)
- `models` — inline semantic model(s) keyed by API name when the caller
  supplies the definition instead of a stored SDM

### Returns (forwarded verbatim)

Unknown nested fields are preserved for the renderer:

- `bundle` — live value, trend/comparison series, status/threshold
- `submetric` — resolved sub-metric when the metric is decomposed
- `sdm` — resolved semantic-model context
- `timeRange` / `unifiedTimeRange` — effective range(s) the bundle used

### Live 404 is backend, not a payload bug

Orgs have returned `UNEXPECTED_ERROR` / `RuntimeException: Post to
/v2/internal/bundle status failed. status code: 404` even with a real
metric + model. The same 404 appears via `render_metric` (same backend
endpoint). **Do not retry as if the body were wrong.** Document the
failure; do not invent a "correct" JWT or SDM pin to work around it.

---

## `render_metric`

Render a semantic metric **card**: current value, trend, forecast, and
insights. Pass the metric `apiName` and the semantic model's `apiName`.
Returns a fully-primed insight-bundle envelope (`sdm` + `bundle` +
`submetric` + resolved `timeRange` + filters + layout) for the
metric-standalone MCP renderer. First paint needs no extra client
round-trips.

Same `/v2/internal/bundle` backend family as `generate_insight_bundle` —
a 404 there is the service, not a missing `apiName`.
