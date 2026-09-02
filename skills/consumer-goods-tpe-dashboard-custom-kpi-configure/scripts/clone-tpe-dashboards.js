#!/usr/bin/env node
/**
 * Deterministic driver for Customization Scenario 1 ("Use Custom KPIs with
 * Standard Dashboards"). Encodes the exact clone recipe validated by hand
 * against a live org (2026-08-17) — every strip/replace rule below
 * was derived from real 400/422 responses, not guessed. See
 * ../references/payload-shapes.md for the annotated trace of how each rule
 * was discovered.
 *
 * What it does, always, for all 5 KPI slots (Promotion Measure 1-3, Tactic
 * Measure 1-2), regardless of which slots have an override:
 *   1. Resolve the installed TPE Analytics app + its asset ids (Extended
 *      SDM, both dashboards) — never hardcoded. Visualization ids are
 *      resolved per-dashboard at clone time (step 4), not here — every
 *      dashboard's own widget list is the source of truth for which
 *      visualizations exist, never a fixed count assumed up front.
 *   2. GET the whole Extended SDM once; index the 5 base parameters +
 *      their matching calculated measurements by apiName (Tactic-side
 *      measurements are apiName `_clc`, not `_value` — never assume symmetry).
 *   3. For each slot, POST a cloned parameter (`<base>_<suffix>`) with a new/
 *      updated default-value entry, then a cloned calculated measurement
 *      whose expression is repointed at the cloned parameter.
 *   4. Clone EVERY visualization referenced by a "visualization"-type widget
 *      on either base dashboard that references at least one of the 5 slot
 *      measurements — confirmed live: on both TPE dashboards, virtually
 *      every chart (top/bottom performers, trend, category breakdowns, not
 *      just the one obviously-named "Performance_Measures" viz) binds to
 *      the same generic KPI-measure fields. Cloning only the one
 *      "designated" viz per dashboard (the original, wrong assumption) left
 *      every other chart still bound to the base measurement/parameter,
 *      silently out of sync with the customer's selection. Discovered by
 *      walking the base dashboard's widgets directly, never by a
 *      hardcoded/guessed visualization template name.
 *   5. Clone the 2 dashboards: repoint parameter-widgets' parameterName and
 *      every visualization-widget's source to its Phase-4 clone — located
 *      dynamically by matching base apiNames inside the widget map, never by
 *      a hardcoded widget key (widget keys like "parameter_3" are
 *      install-specific, not stable across orgs).
 *
 * Never mutates a base artifact — every write here is a new POST of a
 * suffixed copy the base model.
 *
 * CLI usage:
 *   node clone-tpe-dashboards.js --target-org <username> --suffix Cust \
 *     [--overrides '{
 *       "Promotion_Measure_1": {"measureCode":"VOLU","displayName":"Volume"},
 *       "Promotion_Measure_2": {"allowedValues":[{"displayName":"A","value":"AAAA"},{"displayName":"B","value":"BBBB"}],"defaultValue":"A"}
 *     }'] \
 *     [--max-vizs-per-dashboard N] [--dry-run]
 *
 * --overrides is a sparse JSON object keyed by slot
 * (Promotion_Measure_1/2/3, Tactic_Measure_1/2). A slot not present in
 * --overrides still gets a full clone in "append" mode (see below), using
 * the base default measure code and "<base default display name> <suffix>".
 *
 * Two override modes per slot, chosen by which fields are present:
 *   - {measureCode, displayName} — APPEND mode (default): the clone's
 *     allowedValues = the base parameter's full menu + this one new/changed
 *     entry, set as the default selection. The base menu stays fully intact
 *     underneath. Any customer-supplied measureCode/displayName is used
 *     verbatim — it is not required to reuse or embed the suffix.
 *   - {allowedValues: [{displayName, value}, ...], defaultValue?} — REPLACE
 *     mode: the customer supplies the COMPLETE dropdown menu themselves; the
 *     base allowedValues are discarded, not merged. defaultValue must match
 *     one supplied entry's displayName (defaults to the first entry if
 *     omitted). Use this when the customer wants their own measure-code menu
 *     instead of the base 13/14/6-entry standard list.
 *
 * --max-vizs-per-dashboard N — debug/iteration aid only. Caps how many
 * distinct visualizations get cloned per dashboard (e.g. 1 or 2) so a quick
 * validation pass doesn't have to wait through all 9/7 real viz clones.
 * Widgets beyond the cap are left pointing at their base visualization —
 * the dashboard still builds, just without full viz coverage. Omit for a
 * real/complete run — never use this for an actual customer deliverable.
 *
 * --dry-run prints the fully resolved plan (every payload that would be
 * POSTed) and exits 0 without writing anything.
 */

const { restRequest } = require('./sf-rest');

const TEMPLATE_SOURCE_ID = 'sfdc_internal__Trade_Promotion_Effectiveness';
const EXTENDED_MODEL_TEMPLATE_NAME_PREFIX = 'Extended_Trade_Promotion_Management';

const SLOTS = [
  { key: 'Promotion_Measure_1', paramApi: 'Promotion_Measure_1_prm', dashboard: 'Promotion' },
  { key: 'Promotion_Measure_2', paramApi: 'Promotion_Measure_2_prm', dashboard: 'Promotion' },
  { key: 'Promotion_Measure_3', paramApi: 'Promotion_Measure_3_prm', dashboard: 'Promotion' },
  { key: 'Tactic_Measure_1', paramApi: 'Tactic_Measure_1_prm', dashboard: 'Tactic' },
  { key: 'Tactic_Measure_2', paramApi: 'Tactic_Measure_2_prm', dashboard: 'Tactic' },
];

const DASHBOARDS = {
  Promotion: { templateAssetSourceName: 'PromotionAnalysis' },
  Tactic: { templateAssetSourceName: 'TacticAnalysis' },
};

function parseArgs(argv) {
  const args = { dryRun: false };
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--dry-run') { args.dryRun = true; continue; }
    if (!token.startsWith('--')) continue;
    args[token.slice(2).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = argv[i + 1];
    i += 1;
  }
  return args;
}

function requireArg(args, name) {
  if (!args[name]) {
    console.error(`Missing required --${name}`);
    process.exit(2);
  }
  return args[name];
}

async function rest(targetOrg, apiVersion, path, method, body) {
  const result = await restRequest({
    targetOrg,
    path: `/services/data/${apiVersion}${path}`,
    method,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!result.ok) {
    throw new Error(`${method || 'GET'} ${path} -> HTTP ${result.status}: ${JSON.stringify(result.body)}`);
  }
  return result.body;
}

// GET-by-name, tolerating a 404 as "doesn't exist yet" (returns null) instead
// of throwing — confirmed live: /tableau/visualizations/<name> and
// /tableau/dashboards/<name> both resolve by name (not just by Id) and
// return {errorCode: "RESOURCE_NOT_FOUND"} with HTTP 404 when absent, the
// same by-name-GET shape already trusted for /ssot/semantic/models/<apiName>
// above. Any other non-2xx status is a real error and still throws.
async function getIfExists(targetOrg, apiVersion, path) {
  const result = await restRequest({
    targetOrg,
    path: `/services/data/${apiVersion}${path}`,
    method: 'GET',
  });
  if (result.ok) return result.body;
  if (result.status === 404) return null;
  throw new Error(`GET ${path} -> HTTP ${result.status}: ${JSON.stringify(result.body)}`);
}

// Keys that would pollute the clone's prototype if copied via out[k] = v on a
// plain {} — skipped unconditionally in both deep-copy helpers below,
// regardless of the caller's own strip list.
const UNSAFE_KEYS = ['__proto__', 'constructor', 'prototype'];

// Recursively delete the given keys from every plain object in the tree.
function stripKeysDeep(value, keys) {
  if (Array.isArray(value)) return value.map((v) => stripKeysDeep(v, keys));
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      if (keys.includes(k) || UNSAFE_KEYS.includes(k)) continue;
      out[k] = stripKeysDeep(v, keys);
    }
    return out;
  }
  return value;
}

// Recursively delete .label and .type from any object whose .type is
// "Visualization" or "SemanticModel" (source/dynamicTokens[].source refs) —
// confirmed live: these ref objects accept only .name on create. Never
// strip .type from a widget object itself (the polymorphic discriminator).
function stripSourceRefMetadataDeep(value) {
  if (Array.isArray(value)) return value.map(stripSourceRefMetadataDeep);
  if (value && typeof value === 'object') {
    const out = {};
    const isSourceRef = value.type === 'Visualization' || value.type === 'SemanticModel';
    for (const [k, v] of Object.entries(value)) {
      if (UNSAFE_KEYS.includes(k)) continue;
      if (isSourceRef && (k === 'label' || k === 'type')) continue;
      out[k] = stripSourceRefMetadataDeep(v);
    }
    return out;
  }
  return value;
}

function replaceApiNamesInJson(obj, replacements) {
  let text = JSON.stringify(obj);
  for (const [from, to] of replacements) {
    text = text.split(from).join(to);
  }
  return JSON.parse(text);
}

async function resolveApp(targetOrg, apiVersion) {
  const resp = await rest(targetOrg, apiVersion, `/app-framework/apps?templateSourceId=${TEMPLATE_SOURCE_ID}`, 'GET');
  const apps = (resp.apps || resp || []).filter((a) =>
    ['SuccessStatus', 'SuccessWithWarningsStatus'].includes(a.applicationStatus)
  );
  if (apps.length === 0) {
    throw new Error(
      'No successfully installed TPE Analytics app found. Run the setup-tpe-dashboard skill first.'
    );
  }
  if (apps.length > 1) {
    const candidates = apps.map((a) => `${a.id} (${a.name || a.label}, ${a.createdDate})`).join('; ');
    throw new Error(
      `Multiple installed TPE Analytics apps found — refusing to guess which one to target: ${candidates}. Re-run with the intended app disambiguated (not yet a CLI flag; extend this script to accept --app-id if this occurs in practice).`
    );
  }
  return apps[0];
}

async function resolveAssets(targetOrg, apiVersion, appId) {
  const resp = await rest(targetOrg, apiVersion, `/app-framework/apps/${appId}/assets`, 'GET');
  const assets = resp.assets || resp;
  const byTemplateName = {};
  for (const asset of assets) {
    byTemplateName[asset.templateAssetSourceName] = asset;
  }
  const extendedModelAsset = Object.values(byTemplateName).find(
    (a) => a.type === 'SemanticModel' && a.templateAssetSourceName.startsWith(EXTENDED_MODEL_TEMPLATE_NAME_PREFIX)
  );
  if (!extendedModelAsset) throw new Error('Extended TPM Analytics SemanticModel asset not found in app assets.');
  return { assets, byTemplateName, extendedModelAsset };
}

// Two override modes, chosen per-slot by which fields are present:
//  - no override, or {measureCode, displayName}: "append" mode (default) — the
//    clone's allowedValues = base's full list + this one new/changed entry;
//    the base menu stays fully intact, only the default selection changes.
//  - {allowedValues: [{displayName, value}, ...], defaultValue?}: "replace"
//    mode — the customer supplies the COMPLETE dropdown menu themselves; the
//    base allowedValues are discarded entirely, not merged. defaultValue must
//    match one of the supplied entries' displayName (defaults to the first
//    entry if omitted).
function slotOverride(overrides, slotKey, baseDefaultDisplayName, baseDefaultCode, suffix, baseAllowedValues) {
  const o = overrides[slotKey];
  if (!o) {
    return {
      mode: 'append',
      allowedValues: baseAllowedValues,
      measureCode: baseDefaultCode,
      displayName: `${baseDefaultDisplayName} ${suffix}`,
    };
  }
  if (o.allowedValues) {
    if (!Array.isArray(o.allowedValues) || o.allowedValues.length === 0) {
      throw new Error(`Slot ${slotKey}: overrides.allowedValues must be a non-empty array of {displayName, value}.`);
    }
    const defaultDisplayName = o.defaultValue || o.allowedValues[0].displayName;
    const matchingEntry = o.allowedValues.find((v) => v.displayName === defaultDisplayName);
    if (!matchingEntry) {
      throw new Error(
        `Slot ${slotKey}: overrides.defaultValue "${defaultDisplayName}" doesn't match any displayName in overrides.allowedValues.`
      );
    }
    return {
      mode: 'replace',
      allowedValues: o.allowedValues,
      measureCode: matchingEntry.value,
      displayName: defaultDisplayName,
    };
  }
  return {
    mode: 'append',
    allowedValues: baseAllowedValues,
    measureCode: o.measureCode || baseDefaultCode,
    displayName: o.displayName || `${baseDefaultDisplayName} ${suffix}`,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'targetOrg');
  const suffix = requireArg(args, 'suffix');
  const overrides = args.overrides ? JSON.parse(args.overrides) : {};
  const dryRun = args.dryRun;
  // Debug/iteration aid — cap how many distinct visualizations get cloned per
  // dashboard so a full validation pass doesn't require waiting through all
  // 9/7 real viz clones every time. Widgets beyond the cap are left pointing
  // at their base visualization (same as a genuinely-unrelated widget) — the
  // dashboard still builds successfully, just without full viz coverage.
  // Omit for a real/complete run.
  const maxVizsPerDashboard = args.maxVizsPerDashboard ? parseInt(args.maxVizsPerDashboard, 10) : Infinity;

  const { execFileSync } = require('child_process');
  // A color-forcing terminal (e.g. Warp's FORCE_COLOR=3) makes `sf` emit ANSI
  // codes even with --json, which breaks JSON.parse — force color off for
  // this invocation regardless of the calling shell's env.
  const orgDisplay = JSON.parse(
    execFileSync('sf', ['org', 'display', '--target-org', targetOrg, '--json'], {
      encoding: 'utf8',
      env: { ...process.env, FORCE_COLOR: '0', NO_COLOR: '1' },
    })
  ).result;
  if (orgDisplay.connectedStatus !== 'Connected') {
    throw new Error(`Org ${targetOrg} is not connected (connectedStatus=${orgDisplay.connectedStatus}). Log in and retry.`);
  }
  // Pinned per standing instruction — always v67.0, not the org's own apiVersion.
  const apiVersion = 'v67.0';
  console.error(`[info] target-org=${targetOrg} apiVersion=${apiVersion} suffix=${suffix} dryRun=${dryRun}`);

  const app = await resolveApp(targetOrg, apiVersion);
  console.error(`[info] resolved app: ${app.id} (${app.name})`);

  const { byTemplateName, extendedModelAsset } = await resolveAssets(targetOrg, apiVersion, app.id);
  // The model must be addressed by its live apiName for the parameters/
  // calculated-measurements sub-resource paths — resolve it from the model
  // GET itself rather than trusting any asset-list field, since the asset
  // list's naming of the apiName field isn't guaranteed stable.
  const model = await rest(targetOrg, apiVersion, `/ssot/semantic/models/${extendedModelAsset.assetIdOrName}`, 'GET');
  const resolvedModelApiName = model.apiName;
  console.error(`[info] Extended SDM apiName: ${resolvedModelApiName}`);

  const paramsByApi = {};
  for (const p of model.semanticParameters) paramsByApi[p.apiName] = p;
  const measurementsByParamApi = {};
  const measurementsByApi = {};
  for (const m of model.semanticCalculatedMeasurements) {
    measurementsByApi[m.apiName] = m;
    const match = m.expression && m.expression.match(/\[Parameters\]\.\[([A-Za-z0-9_]+)\]/);
    if (match) measurementsByParamApi[match[1]] = m;
  }

  const plan = SLOTS.map((slot) => {
    const baseParam = paramsByApi[slot.paramApi];
    if (!baseParam) throw new Error(`Base parameter ${slot.paramApi} not found in Extended SDM.`);
    const baseMeasurement = measurementsByParamApi[slot.paramApi];
    if (!baseMeasurement) throw new Error(`No calculated measurement references parameter ${slot.paramApi}.`);
    const baseDefaultEntry = baseParam.allowedValues.find((v) => v.displayName === baseParam.defaultValue);
    if (!baseDefaultEntry) throw new Error(`Base parameter ${slot.paramApi}'s defaultValue doesn't match any allowedValues entry.`);

    const resolved = slotOverride(
      overrides, slot.key, baseDefaultEntry.displayName, baseDefaultEntry.value, suffix, baseParam.allowedValues
    );
    const newParamApi = `${slot.paramApi}_${suffix}`;
    const newMeasurementApi = `${baseMeasurement.apiName}_${suffix}`;

    return {
      ...slot,
      baseParamApi: slot.paramApi,
      baseMeasurementApi: baseMeasurement.apiName,
      newParamApi,
      newMeasurementApi,
      baseParamLabel: baseParam.label,
      newParamLabel: `${baseParam.label} ${suffix}`,
      resolved,
      newParamBody: {
        apiName: newParamApi,
        label: `${baseParam.label} ${suffix}`,
        type: baseParam.type,
        dataType: baseParam.dataType,
        // APPEND mode upserts by measureCode (allowedValues[].value is unique
        // in the base menu) — if the customer's chosen code already exists
        // (e.g. picking an existing code with a new displayName), replace
        // that entry's displayName in place rather than adding a duplicate
        // value with two different labels.
        allowedValues: resolved.mode === 'replace'
          ? resolved.allowedValues
          : [
              ...baseParam.allowedValues.filter((v) => v.value !== resolved.measureCode),
              { displayName: resolved.displayName, value: resolved.measureCode },
            ],
        defaultValue: resolved.displayName,
      },
      newMeasurementBody: {
        apiName: newMeasurementApi,
        label: `${baseMeasurement.label} ${suffix}`,
        dataType: baseMeasurement.dataType,
        aggregationType: baseMeasurement.aggregationType,
        totalAggregationType: baseMeasurement.totalAggregationType,
        level: baseMeasurement.level,
        isQueryable: baseMeasurement.isQueryable,
        isVisible: baseMeasurement.isVisible,
        directionality: baseMeasurement.directionality,
        sentiment: baseMeasurement.sentiment,
        shouldTreatNullsAsZeros: baseMeasurement.shouldTreatNullsAsZeros,
        expression: baseMeasurement.expression.split(`[${slot.paramApi}]`).join(`[${newParamApi}]`),
      },
    };
  });

  console.error('[plan] resolved 5-slot plan:');
  for (const p of plan) {
    console.error(
      `  ${p.key}: ${p.baseParamApi} -> ${p.newParamApi} | ${p.baseMeasurementApi} -> ${p.newMeasurementApi} | mode=${p.resolved.mode} measureCode=${p.resolved.measureCode} displayName="${p.resolved.displayName}" allowedValuesCount=${p.resolved.allowedValues.length}`
    );
  }

  if (dryRun) {
    console.log(JSON.stringify({ dryRun: true, plan }, null, 2));
    return;
  }

  const created = { parameters: {}, measurements: {}, visualizations: {}, dashboards: {} };

  for (const p of plan) {
    // Resumable: a prior run of this same suffix may have already created
    // this slot's parameter/measurement (e.g. an interrupted run). The model
    // was freshly re-fetched above, so an existing clone shows up here —
    // reuse it rather than re-POSTing into apiName-uniqueness
    // CREATE_SEMANTIC_ENTITY_FAILED. Never re-derive an existing artifact's
    // fields from the plan; trust the live model as the source of truth.
    const existingParam = paramsByApi[p.newParamApi];
    const paramResp = existingParam
      ? existingParam
      : await rest(targetOrg, apiVersion, `/ssot/semantic/models/${resolvedModelApiName}/parameters`, 'POST', p.newParamBody);
    created.parameters[p.key] = paramResp;
    console.error(`[${existingParam ? 'exists' : 'created'}] parameter ${p.newParamApi} (id ${paramResp.id})`);

    const existingMeasurement = measurementsByApi[p.newMeasurementApi];
    const measResp = existingMeasurement
      ? existingMeasurement
      : await rest(targetOrg, apiVersion, `/ssot/semantic/models/${resolvedModelApiName}/calculated-measurements`, 'POST', p.newMeasurementBody);
    created.measurements[p.key] = measResp;
    console.error(`[${existingMeasurement ? 'exists' : 'created'}] calculated measurement ${p.newMeasurementApi} (id ${measResp.id})`);
  }

  for (const [dashKey, dashCfg] of Object.entries(DASHBOARDS)) {
    const dashAsset = byTemplateName[dashCfg.templateAssetSourceName];
    if (!dashAsset) throw new Error(`Dashboard asset ${dashCfg.templateAssetSourceName} not found.`);
    const baseDash = await rest(targetOrg, apiVersion, `/tableau/dashboards/${dashAsset.assetIdOrName}`, 'GET');

    const slotsForDash = plan.filter((p) => p.dashboard === dashKey);
    const measurementReplacements = slotsForDash.map((p) => [p.baseMeasurementApi, p.newMeasurementApi]);
    const paramReplacements = slotsForDash.map((p) => [p.baseParamApi, p.newParamApi]);
    // Cosmetic fields[].label text embeds the PARAMETER'S LABEL, not its apiName
    // (e.g. "<[Parameters].[Promotion Measure 1]>") — confirmed live: fieldName
    // is correctly repointed by measurementReplacements, but this display string
    // is untouched unless we also replace the label text inside the
    // "[Parameters].[<label>]" pattern specifically (not a bare label replace,
    // which risks clobbering unrelated text that happens to contain the label).
    // Some cosmetic label strings store the surrounding angle brackets as
    // literal `<`/`>`, others as HTML entities (`&lt;`/`&gt;`) depending on
    // where the platform rendered them from — confirmed live: an
    // entity-escaped occurrence left untouched by a plain-bracket-only
    // replacement re-serializes as `&lt;[Parameters].[<label> Cust]&gt;`
    // instead of decoding to `<...>`. Handle the entity-escaped form first
    // (converting it to plain `<...>` in the same pass) before the
    // plain-bracket fallback for any remaining unescaped occurrences.
    const labelReplacements = slotsForDash.flatMap((p) => [
      [`&lt;[Parameters].[${p.baseParamLabel}]&gt;`, `<[Parameters].[${p.newParamLabel}]>`],
      [`[Parameters].[${p.baseParamLabel}]`, `[Parameters].[${p.newParamLabel}]`],
    ]);
    const allReplacements = [...paramReplacements, ...measurementReplacements, ...labelReplacements];

    // Discover every "visualization"-type widget's source viz by walking the
    // base dashboard directly (never a hardcoded/guessed viz template name)
    // and clone each one that actually references at least one of this
    // dashboard's slot measurements — confirmed live: virtually every chart
    // on both TPE dashboards binds to the same generic KPI-measure fields,
    // not just one "designated" viz. A viz genuinely unrelated to these
    // slots (no measurement apiName present) is left pointing at base.
    const vizWidgets = Object.values(baseDash.widgets).filter((w) => w.type === 'visualization');
    const clonedVizNameByBase = {};
    for (const widget of vizWidgets) {
      const baseVizName = widget.source.name;
      if (clonedVizNameByBase[baseVizName]) continue; // already cloned (widget reuses same viz)
      if (Object.keys(clonedVizNameByBase).length >= maxVizsPerDashboard) {
        console.error(`[debug] --max-vizs-per-dashboard=${maxVizsPerDashboard} reached for ${dashKey}; leaving ${baseVizName} on base`);
        continue;
      }
      const baseViz = await rest(targetOrg, apiVersion, `/tableau/visualizations/${widget.source.id}`, 'GET');
      const vizJson = JSON.stringify(baseViz);
      const relevantMeasurementReplacements = measurementReplacements.filter(([from]) => vizJson.includes(from));
      if (relevantMeasurementReplacements.length === 0) continue; // genuinely unrelated to these slots
      const relevantLabelReplacements = labelReplacements.filter(([from]) => vizJson.includes(from));
      const relevantReplacements = [...relevantMeasurementReplacements, ...relevantLabelReplacements];

      // Unlike the dashboard body below, the visualization's own dataSource
      // ref (type: "SemanticModel") must keep its .type — confirmed live:
      // stripping it here (as stripSourceRefMetadataDeep would) causes
      // INVALID_INPUT "Value required for [type]." stripSourceRefMetadataDeep
      // is only valid for dashboard widget source/dynamicTokens refs.
      let vizBody = stripKeysDeep(baseViz, [
        'id', 'createdBy', 'createdDate', 'lastModifiedBy', 'lastModifiedDate',
        'permissions', 'sourceVersion', 'templateSource', 'url', 'status',
      ]);
      if (vizBody.view) delete vizBody.view.isOriginal;
      vizBody = replaceApiNamesInJson(vizBody, relevantReplacements);
      vizBody.name = `${baseViz.name}_${suffix}`;
      vizBody.label = `${baseViz.label} ${suffix}`;

      // Resumable, same as the parameter/measurement loop above: a prior
      // interrupted run may have already created this clone. GET-by-name
      // first rather than re-POSTing into a name-uniqueness failure — never
      // re-derive an existing clone's body from the current plan; trust
      // whatever is already live in the org.
      const existingViz = await getIfExists(targetOrg, apiVersion, `/tableau/visualizations/${vizBody.name}`);
      const vizResp = existingViz || await rest(targetOrg, apiVersion, '/tableau/visualizations', 'POST', vizBody);
      clonedVizNameByBase[baseVizName] = vizResp.name;
      created.visualizations[`${dashKey}:${baseVizName}`] = vizResp;
      console.error(`[${existingViz ? 'exists' : 'created'}] visualization ${vizBody.name} (id ${vizResp.id})`);
    }

    let dashBody = { ...baseDash };
    delete dashBody.customViews;
    dashBody = stripKeysDeep(dashBody, [
      'id', 'createdBy', 'createdDate', 'lastModifiedBy', 'lastModifiedDate',
      'permissions', 'sourceVersion', 'templateSource', 'url', 'status',
    ]);
    dashBody = stripSourceRefMetadataDeep(dashBody);
    dashBody = replaceApiNamesInJson(dashBody, allReplacements);
    dashBody.name = `${baseDash.name}_${suffix}`;
    dashBody.label = `${baseDash.label} ${suffix}`;

    // Repoint every visualization widget at its clone (by base name) —
    // widgets whose viz had no relevant measurement are left untouched,
    // still pointing at the base visualization.
    for (const widget of Object.values(dashBody.widgets)) {
      if (widget.type === 'visualization' && clonedVizNameByBase[widget.source.name]) {
        widget.source.name = clonedVizNameByBase[widget.source.name];
      }
    }

    // Resumable, same rationale as the visualization loop above: GET-by-name
    // before POSTing so a re-run after a prior partial failure reuses an
    // already-created dashboard clone instead of hitting a name-uniqueness
    // error.
    const existingDash = await getIfExists(targetOrg, apiVersion, `/tableau/dashboards/${dashBody.name}`);
    const dashResp = existingDash || await rest(targetOrg, apiVersion, '/tableau/dashboards', 'POST', dashBody);
    created.dashboards[dashKey] = dashResp;
    console.error(`[${existingDash ? 'exists' : 'created'}] dashboard ${dashBody.name} (id ${dashResp.id})`);
  }

  console.log(JSON.stringify({
    parameters: Object.fromEntries(Object.entries(created.parameters).map(([k, v]) => [k, { apiName: v.apiName, id: v.id }])),
    measurements: Object.fromEntries(Object.entries(created.measurements).map(([k, v]) => [k, { apiName: v.apiName, id: v.id }])),
    visualizations: Object.fromEntries(Object.entries(created.visualizations).map(([k, v]) => [k, { name: v.name, id: v.id }])),
    dashboards: Object.fromEntries(Object.entries(created.dashboards).map(([k, v]) => [k, { name: v.name, id: v.id }])),
  }, null, 2));
}

main().catch((err) => {
  console.error(`[error] ${err.message}`);
  process.exit(1);
});
