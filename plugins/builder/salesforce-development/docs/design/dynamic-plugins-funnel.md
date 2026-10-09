# Dynamic Plugins funnel telemetry

This is the analytics contract for W-24163509. It keeps the producer's established
`command.invoked` shape intact and defines one consistent recommend-to-install funnel for the
dashboard.

## Definitions

- **Headline recommendations:** unique `(plugin, session)` recommendations that were likely shown.
  A medium-confidence `bypass-gate` event is a soft advisory that often never reaches the visible
  user surface, so it is excluded from this headline.
- **Soft advisories:** unique `(plugin, session)` medium-confidence `bypass-gate` recommendations.
  Show this as a separate diagnostic tile, not as part of the headline numerator.
- **Installs:** unique `(plugin, session)` `plugin.installed` events. This remains designed-path
  conversion; out-of-band installs are not inferred.
- **Conversion:** unique installs divided by unique shown recommendations. Use the same distinct key
  in the headline and every surface/plugin breakdown.
- **Raw events:** a diagnostic volume only. If retained, label the tile **Raw recommendation
  events**; never label it unique.

The recommended dashboard label is **Unique plugin-session recommendations shown**. It matches the
deduplicated query and describes the metric more usefully than preserving the old near-raw value.

## Recommendation-setting changes

Successful preference mutations made through
`/salesforce-development:plugin-recommendations` emit the internal event
`plugin_recommendation_configured`, projected to PDP/UIP as
`pluginRecommendation.configured` with `componentId = 'sensitivity'`,
`contextName = 'action::level'`, and `contextValue = '<action>::<level>'`.

The action vocabulary is `disable`, `reset`, and `set`; the level vocabulary is `off`, `default`,
`low`, `standard`, `high`, and `custom`. `off` and `set off` both produce `disable::off`; `on`
produces `reset::default`; named `set` values retain their level; numeric thresholds produce
`set::custom`. The exact custom number, raw argument, previous value, preference path, prompt, and
environment values are never captured.

This event measures successful slash-command actions only. It does not observe native `userConfig`
or environment-variable changes, and a saved choice can be masked by a higher-precedence environment
setting. `reset` means the saved override was cleared so resolution returns to the plugin/install
default; it does not mean the command forced `standard`. Repeated successful commands produce
repeated events.

For user-choice metrics, count distinct `machine_id`; raw row counts measure actions, not users:

```sql
SELECT
  recommendation_setting_action,
  recommendation_setting_level,
  approx_distinct(machine_id) AS unique_users
FROM events
WHERE event_name = 'pluginRecommendation.configured'
GROUP BY 1, 2
ORDER BY 1, 2;
```

Use `COUNT(*) AS configuration_actions` over the same grouping only when the dashboard is explicitly
labelled as action volume.

## Producer result reasons

`pluginInstall.completed` has the catalog-validated plugin name as `componentId`,
`contextName = 'reason'`, and one of these fixed `contextValue` values. When the input cannot be
validated against the catalog, `componentId` is the fixed sentinel `unknown`; caller-supplied text
never reaches telemetry.

| Class | Reasons |
| --- | --- |
| Completed | `installed`, `previewed`, `declined` |
| No install attempt | `usage_error`, `invalid_name`, `catalog_unreadable`, `unknown_plugin`, `self_plugin`, `already_installed`, `decline_refused`, `proposal_not_selected` |
| Retryable confirmation | `stale_nonce` |
| Genuine install failure | `subprocess_failure` |

Only `subprocess_failure` is the actual `claude plugin install` failure signal. The existing
`command.invoked` `outcome = 'failure'` remains a nonzero-exit signal for backwards compatibility.

## Correct nested-message projection

Always bound `ts_date` in the innermost scan. `_userPayloadData` contains `message` as a JSON string,
so fields require two `JSON_EXTRACT_SCALAR` calls. Event names are emitter-prefixed and must be
reduced to their final segment.

```sql
WITH source_events AS (
  SELECT
    rawtimestamp,
    ts_date,
    TRY(JSON_EXTRACT_SCALAR(_userPayloadData, '$.message')) AS message_json
  FROM uip_iceberg.coreapplogs_v4t.uxlog_view
  WHERE ts_date >= '<START_YYYYMMDD>'
    AND _userPayloadSchemaName = 'sf.a4dInstrumentation.A4dInstrumentation'
    AND _userPayloadData LIKE '%salesforce-development/%'
),
events AS (
  SELECT
    rawtimestamp,
    REGEXP_EXTRACT(
      TRY(JSON_EXTRACT_SCALAR(message_json, '$.eventName')), '[^/]+$'
    ) AS event_name,
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.session_Id')) AS session_id,
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.componentId')) AS component_id,
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.contextName')) AS context_name,
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.contextValue')) AS context_value,
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.skillSource')) AS skill_source
  FROM source_events
),
lifecycle AS (
  SELECT
    event_name,
    session_id,
    component_id AS plugin,
    SPLIT_PART(context_value, '::', 2) AS confidence,
    SPLIT_PART(context_value, '::', 3) AS surface
  FROM events
  WHERE skill_source = 'salesforce-development'
    AND event_name IN ('plugin.recommended', 'plugin.installed')
    AND context_name = 'origin::confidence::surface'
)
SELECT event_name, COUNT(*) AS raw_events
FROM lifecycle
GROUP BY 1
ORDER BY 1;
```

Do not use quoted-fragment `LIKE` tests against `_userPayloadData`; its inner quotes are escaped.
For a cheap existence check, match an unquoted fragment such as `%pluginInstall.completed%`.

## Headline and shown-versus-counted split

Append these CTEs to the projection above:

```sql
, recommendation_observations AS (
  SELECT DISTINCT
    plugin,
    session_id,
    confidence,
    surface,
    CASE
      WHEN surface = 'bypass-gate' AND confidence = 'medium' THEN 'soft_advisory'
      ELSE 'shown'
    END AS visibility
  FROM lifecycle
  WHERE event_name = 'plugin.recommended'
), recommendation_keys AS (
  SELECT
    plugin,
    session_id,
    CASE
      WHEN COUNT_IF(visibility = 'shown') > 0 THEN 'shown'
      ELSE 'soft_advisory'
    END AS visibility
  FROM recommendation_observations
  GROUP BY 1, 2
), surface_recommendation_keys AS (
  SELECT DISTINCT plugin, session_id, surface
  FROM recommendation_observations
  WHERE visibility = 'shown'
), install_keys AS (
  SELECT DISTINCT plugin, session_id, surface
  FROM lifecycle
  WHERE event_name = 'plugin.installed'
), shown_install_keys AS (
  SELECT DISTINCT i.plugin, i.session_id
  FROM install_keys i
  JOIN recommendation_keys r
    ON r.plugin = i.plugin
   AND r.session_id = i.session_id
   AND r.visibility = 'shown'
)
SELECT
  COUNT_IF(visibility = 'shown') AS unique_plugin_sessions_shown,
  COUNT_IF(visibility = 'soft_advisory') AS unique_plugin_sessions_soft_advisory,
  (SELECT COUNT(*) FROM shown_install_keys) AS unique_shown_installs,
  1.0 * (SELECT COUNT(*) FROM shown_install_keys)
    / NULLIF(COUNT_IF(visibility = 'shown'), 0) AS shown_to_install_ratio
FROM recommendation_keys;
```

The ratio is intentionally returned on a 0–1 scale. In Superset, format it with `,.1%`; do not
also multiply it by 100 in SQL.

## Per-surface funnel

The install event recovers the proposal surface before the proposal marker is cleared. Keep
`self-directed` installs separate because they have no recommendation denominator.

```sql
SELECT
  r.surface,
  COUNT(*) AS unique_plugin_sessions_shown,
  COUNT(i.plugin) AS unique_plugin_sessions_installed,
  1.0 * COUNT(i.plugin) / NULLIF(COUNT(*), 0) AS conversion_ratio
FROM surface_recommendation_keys r
LEFT JOIN install_keys i
  ON i.plugin = r.plugin
 AND i.session_id = r.session_id
 AND i.surface = r.surface
GROUP BY 1
ORDER BY 1;
```

For the plugin-by-surface view, add `r.plugin` to the select and group by both dimensions.

## Match reason

`plugin.recommended`, `plugin.loaded`, `plugin.installed`, and `pluginSuggestion.declined` also
record why the suggestion fired, as two named UIP attributes in the same bag as `skillSource`:
`matchKeywords` and `matchSignal` (the Skills dashboard reads them as `$.properties.matchKeywords` /
`$.properties.matchSignal`; this note's projection reads `$.matchKeywords` / `$.matchSignal` from
`message_json`). Neither is ever prompt text.

- **`matchKeywords`** is the sorted, comma-joined set of tokens from that plugin's own curated
  catalog `keywords` and `anchorTerms` that were part of the scorer's match evidence, capped at 8
  tokens and 120 characters (a truncated set keeps the alphabetically first tokens). A word the user
  typed that the catalog does not curate can never appear: the producer intersects the evidence with
  the curated vocabulary next to the scorer (`plugin_catalog.curated_match_terms`; see
  [plugin-catalog.md](./plugin-catalog.md)), and the telemetry layer revalidates every token against
  the shipped `catalog/plugins.json` at capture and again at egress. On `session-start` the scored
  text is the signal's fixed query, so there `matchSignal` is the informative dimension.
- **`matchSignal`** is `lwc`, `react`, `agentforce`, or `cms`, set only when
  `surface = 'session-start'`. Signals are matched in that fixed order, and v1 records only the
  first one that surfaced the plugin; later signals for the same plugin in the same scan are not
  aggregated. Capture accepts a sorted, de-duplicated comma-joined set of the codes, so split it
  rather than assume one value.
- **`''`** means no curated evidence — the deterministic test-drive surfaces (recorded as
  `user-prompt`), self-directed installs, a match carried only by description or example-prompt
  words, or (later-turn events only) a proposal ledger that shed the reason to stay under its size
  cap — or a record buffered before the field existed. A **missing** property (`NULL` after
  extraction) means a producer version that predates the field.

`plugin.loaded`, `plugin.installed`, and `pluginSuggestion.declined` inherit the reason recorded
with the plugin's first proposal in the session, exactly as they inherit `surface`; a repeat match
never rewrites it, so short of a ledger shed every stage of one plugin-session funnel carries the
same reason. The PDP `origin::confidence::surface` tuple is deliberately unchanged: if a PDP
consumer ever needs the reason, add a new `contextName`, never a fourth `::` segment that existing
parsers would mis-split. `telemetry-flush.js` forwards the attributes untouched.

Add both attributes to the projection's `events` CTE, after `skill_source`:

```sql
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.skillSource')) AS skill_source,
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.matchKeywords')) AS match_keywords,
    TRY(JSON_EXTRACT_SCALAR(message_json, '$.matchSignal')) AS match_signal
```

Then compare recommended, declined, and installed plugin-sessions per curated keyword:

```sql
SELECT
  component_id AS plugin,
  keyword,
  COUNT(DISTINCT IF(event_name = 'plugin.recommended', session_id)) AS recommended_sessions,
  COUNT(DISTINCT IF(event_name = 'pluginSuggestion.declined', session_id)) AS declined_sessions,
  COUNT(DISTINCT IF(event_name = 'plugin.installed', session_id)) AS installed_sessions
FROM events
CROSS JOIN UNNEST(SPLIT(match_keywords, ',')) AS k (keyword)
WHERE skill_source = 'salesforce-development'
  AND event_name IN ('plugin.recommended', 'pluginSuggestion.declined', 'plugin.installed')
  AND context_name = 'origin::confidence::surface'
  AND match_keywords <> ''
GROUP BY 1, 2
ORDER BY plugin, recommended_sessions DESC;
```

A plugin-session counts once under each of its keywords, so keyword rows do not sum to plugin
totals. The rows include medium `bypass-gate` soft advisories; exclude them as in the headline split
before comparing against shown recommendations. Slice `session-start` rows by `match_signal` the
same way.

## Install result validation

After the producer version is deployed, validate the closed vocabulary with:

```sql
SELECT component_id AS plugin, context_value AS reason, COUNT(*) AS invocations
FROM events
WHERE skill_source = 'salesforce-development'
  AND event_name = 'pluginInstall.completed'
  AND context_name = 'reason'
GROUP BY component_id, context_value
ORDER BY component_id, invocations DESC;
```

The result must contain only the documented vocabulary. Report subprocess install-attempt failure
rate as `subprocess_failure / (subprocess_failure + installed)`; previews and refusals never launch
the install subprocess and therefore do not belong in that denominator. Do not derive this rate
from nonzero `command.invoked` rows.
