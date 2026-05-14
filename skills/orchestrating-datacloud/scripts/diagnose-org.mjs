#!/usr/bin/env node
import { spawnSync } from 'node:child_process';

const HELP = `Data Cloud org readiness classifier

Usage:
  node diagnose-org.mjs -o <orgAlias> [--json] [--phase <phase>] [--describe-table <table>] [--timeout <seconds>]

Options:
  -o, --target-org     Salesforce org alias or username (required)
      --json           Print machine-readable JSON
      --phase          Optional phase focus: all | connect | prepare | harmonize | segment | act | retrieve
      --describe-table Optional DMO/DLO table name for a retrieve-plane probe
      --timeout        Per-command timeout in seconds (default: 45)
  -h, --help           Show this help text
`;

const FEATURE_GUIDANCE = {
  CdpDataStreams: 'Data Streams are unavailable for this org/user. Review Data Cloud Setup provisioning, ingestion-related feature availability, and source connector permissions before using preparing-datacloud.',
  CdpIdentityResolution: 'Identity Resolution is unavailable for this org/user. Review Data Cloud harmonization/identity-resolution entitlements and the user\'s Data Cloud permissions before using harmonizing-datacloud for IR work.',
  CdpActivationTarget: 'Activation Targets are unavailable for this org/user. Review activation permissions, destination setup, and any org-specific activation enablement before using activating-datacloud.',
  CdpActivationExternalPlatform: 'Activation destination platforms are unavailable for this org/user. Review Activation Targets setup, destination auth/configuration, and any feature toggles exposed in Data Cloud Setup → Feature Manager.',
  CdpDataSpace: 'Data Spaces are unavailable for this org/user. Review core Data Cloud provisioning and user permissions in Data Cloud Setup before assuming downstream phases can work.',
};

const CAVEATS = [
  'sf data360 doctor is advisory only: the current upstream command checks the search-index endpoint, not every Data Cloud module.',
  'Do not use query describe as a universal tenant probe. Run it only after confirming broader readiness and only against a known DMO or DLO table.',
  'Core Data Cloud provisioning, tenant creation, and license assignment are not reliably exposed as a full CLI enablement flow. Use CLI detection plus Setup guidance instead of promising fully programmatic enablement.',
];

function parseArgs(argv) {
  const args = { phase: 'all', timeout: 45, json: false, describeTable: null };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    switch (arg) {
      case '-o':
      case '--target-org':
        args.targetOrg = argv[++i];
        break;
      case '--phase':
        args.phase = argv[++i] ?? 'all';
        break;
      case '--describe-table':
        args.describeTable = argv[++i] ?? null;
        break;
      case '--timeout':
        args.timeout = Number(argv[++i] ?? '45');
        break;
      case '--json':
        args.json = true;
        break;
      case '-h':
      case '--help':
        args.help = true;
        break;
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function trimText(text) {
  return (text || '').replace(/\u001b\[[0-?]*[ -/]*[@-~]/g, '').trim();
}

function runCommand(command, args, { json = false, timeoutSeconds = 45 } = {}) {
  const finalArgs = [...args];
  if (json && !finalArgs.includes('--json')) finalArgs.push('--json');
  const result = spawnSync(command, finalArgs, {
    encoding: 'utf8',
    timeout: timeoutSeconds * 1000,
  });

  const stdout = result.stdout || '';
  const stderr = result.stderr || '';
  let parsed = null;
  if (stdout.trim()) {
    try {
      parsed = JSON.parse(stdout);
    } catch {
      parsed = null;
    }
  }

  let errorMessage = null;
  if (result.error) {
    if (result.error.code === 'ENOENT') {
      errorMessage = `${command} is not installed or not on PATH.`;
    } else if (result.error.code === 'ETIMEDOUT') {
      errorMessage = `Timed out after ${timeoutSeconds}s`;
    } else {
      errorMessage = result.error.message;
    }
  }

  return {
    command: [command, ...finalArgs].join(' '),
    exitCode: typeof result.status === 'number' ? result.status : 1,
    stdout: trimText(stdout),
    stderr: trimText(stderr),
    parsed,
    errorMessage,
  };
}

function extractSuccessSample(parsed) {
  const result = parsed?.result ?? {};

  if (Array.isArray(result?.data)) {
    return result.data[0] ?? null;
  }
  if (Array.isArray(result?.data?.platforms)) {
    return result.data.platforms[0] ?? null;
  }
  if (Array.isArray(result?.semanticSearchDefinitionDetails)) {
    return result.semanticSearchDefinitionDetails[0] ?? null;
  }
  return null;
}

function extractDetails(parsed) {
  const result = parsed?.result ?? {};
  if (result && typeof result === 'object' && !Array.isArray(result)) {
    const details = { ...result };
    delete details.data;
    if (details.status || details.indexCount !== undefined || details.apiVersion || details.instanceUrl) {
      return details;
    }
  }
  return undefined;
}

function extractCount(parsed) {
  const result = parsed?.result ?? {};
  if (Array.isArray(result?.data)) return result.data.length;
  if (typeof result?.totalSize === 'number') return result.totalSize;
  if (Array.isArray(result?.data?.platforms)) return result.data.platforms.length;
  if (typeof result?.indexCount === 'number') return result.indexCount;
  return null;
}

function classifyError(message) {
  const text = message || '';
  const gateMatch = text.match(/\[([A-Za-z0-9]+)\]/);

  if (text.includes("Couldn't find CDP tenant ID")) {
    return {
      state: 'query_service_unavailable',
      code: 'QUERY_SERVICE_TENANT_LOOKUP_FAILED',
      reason: 'The query service could not resolve a CDP tenant for this org context. Confirm broader readiness with data-space, DMO, or doctor probes before declaring Data Cloud fully disabled.',
    };
  }
  if (text.includes('This feature is not currently enabled for this user type or org')) {
    const featureCode = gateMatch?.[1] ?? 'UNKNOWN_FEATURE_GATE';
    return {
      state: 'feature_gated',
      code: featureCode,
      reason: FEATURE_GUIDANCE[featureCode] ?? 'This capability is gated for the current org or user. Review provisioning, permissions, and any relevant setup toggles before proceeding.',
    };
  }
  if (text.includes('NOT_FOUND: DataModelEntity')) {
    return {
      state: 'table_not_found',
      code: 'DATA_MODEL_ENTITY_NOT_FOUND',
      reason: 'The specified DMO or DLO table name is not queryable in this org. Pick a real table from dmo list / dlo list or use dmo get first.',
    };
  }
  if (text.includes('Request failed')) {
    return {
      state: 'request_failed',
      code: 'REQUEST_FAILED',
      reason: 'The endpoint returned a generic request failure. Treat this as inconclusive and confirm readiness with adjacent read-only probes.',
    };
  }
  if (text.includes('is not a sf command') || text.includes('not installed or not on PATH')) {
    return {
      state: 'runtime_missing',
      code: 'RUNTIME_MISSING',
      reason: 'The sf data360 runtime is not available. Install or relink the community plugin first.',
    };
  }
  if (text.includes('Timed out after')) {
    return {
      state: 'timeout',
      code: 'TIMEOUT',
      reason: 'The probe timed out. Retry, reduce the scope, or fall back to a smaller read-only command family.',
    };
  }
  return {
    state: 'unknown_error',
    code: 'UNKNOWN_ERROR',
    reason: 'The probe failed for an unclassified reason. Inspect the raw message and confirm readiness with neighboring probes.',
  };
}

function normalizeProbe(name, raw, meta = {}) {
  const base = {
    name,
    command: raw.command,
    exitCode: raw.exitCode,
    stderr: raw.stderr || undefined,
    ...meta,
  };

  if (raw.errorMessage) {
    const error = classifyError(raw.errorMessage);
    return { ...base, ...error, message: raw.errorMessage };
  }

  if (raw.parsed && (raw.parsed.status === 0 || raw.exitCode === 0)) {
    const count = extractCount(raw.parsed);
    const sample = extractSuccessSample(raw.parsed);
    const details = extractDetails(raw.parsed);
    let state = 'ok';
    if (count !== null) {
      state = count > 0 ? 'enabled_populated' : 'enabled_empty';
    }
    if (raw.parsed?.result?.status === 'ok') {
      state = 'ok';
    }
    return {
      ...base,
      state,
      count,
      sample: sample ?? undefined,
      details,
    };
  }

  const message = raw.parsed?.message || raw.stdout || raw.stderr || `Command failed with exit code ${raw.exitCode}`;
  const error = classifyError(message);
  return { ...base, ...error, message };
}

function summarizePhase(checks) {
  const states = Object.values(checks).map((check) => check.state);
  if (states.length === 0) return 'skipped';
  if (states.every((state) => state === 'skipped')) return 'skipped';
  const hasSuccess = states.some((state) => ['ok', 'enabled_empty', 'enabled_populated'].includes(state));
  const hasPopulated = states.includes('enabled_populated');
  const hasBlocking = states.some((state) => ['feature_gated', 'query_service_unavailable', 'request_failed', 'table_not_found', 'timeout', 'unknown_error'].includes(state));
  if (hasSuccess && hasBlocking) return 'partial';
  if (hasPopulated) return 'ready';
  if (hasSuccess) return 'ready_empty';
  if (states.every((state) => state === 'feature_gated')) return 'feature_gated';
  if (states.every((state) => state === 'query_service_unavailable')) return 'query_unavailable';
  if (states.every((state) => ['request_failed', 'timeout', 'unknown_error'].includes(state))) return 'blocked';
  return 'unknown';
}

function guidanceFromProbe(scope, probe) {
  if (!probe) return [];
  if (['ok', 'enabled_empty', 'enabled_populated', 'skipped'].includes(probe.state)) return [];

  if (probe.state === 'runtime_missing') {
    return [
      'Install or relink the community sf data360 runtime before attempting Data Cloud work.',
      'Use python3 ~/.claude/sf-skills-install.py --with-datacloud-runtime or bash ~/.claude/skills/orchestrating-datacloud/scripts/bootstrap-plugin.sh.',
    ];
  }

  if (probe.state === 'query_service_unavailable') {
    return [
      `${scope}: query-specific tenant lookup failed. Do not treat this as a global Data Cloud outage by itself. Re-check core probes such as data-space list, dmo list, and doctor, then use a known table name if you retry query describe.`,
    ];
  }

  if (probe.state === 'feature_gated') {
    return [`${scope}: ${probe.reason}`];
  }

  if (probe.state === 'table_not_found') {
    return [`${scope}: ${probe.reason}`];
  }

  if (probe.state === 'request_failed') {
    return [
      `${scope}: ${probe.reason}`,
      'If doctor is the failing probe, remember that it only checks search indexes; use adjacent read-only probes before deciding the whole org is blocked.',
    ];
  }

  if (probe.state === 'timeout') {
    return [`${scope}: ${probe.reason}`];
  }

  return [`${scope}: ${probe.reason}`];
}

function parseOrgDisplay(raw, targetOrg) {
  const base = {
    alias: targetOrg,
    state: 'ok',
  };

  if (raw.errorMessage) {
    return { ...base, state: 'org_not_authenticated', message: raw.errorMessage };
  }

  if (raw.parsed && raw.parsed.status === 0) {
    const result = raw.parsed.result || {};
    return {
      ...base,
      alias: result.alias || targetOrg,
      username: result.username,
      instanceUrl: result.instanceUrl,
      apiVersion: result.apiVersion,
      connectedStatus: result.connectedStatus,
    };
  }

  const message = raw.parsed?.message || raw.stdout || raw.stderr || `Failed to resolve org ${targetOrg}`;
  return {
    ...base,
    state: 'org_not_authenticated',
    message,
  };
}

function buildProbeMatrix(orgAlias, describeTable) {
  return {
    core: {
      doctor: ['data360', 'doctor', '-o', orgAlias],
      dataSpaces: ['data360', 'data-space', 'list', '-o', orgAlias],
      dmos: ['data360', 'dmo', 'list', '-o', orgAlias],
    },
    phases: {
      connect: {
        connectorCatalog: ['data360', 'connection', 'connector-list', '-o', orgAlias],
        connectionsSalesforceCRM: ['data360', 'connection', 'list', '-o', orgAlias, '--connector-type', 'SalesforceCRM'],
      },
      prepare: {
        dataStreams: ['data360', 'data-stream', 'list', '-o', orgAlias],
        dlos: ['data360', 'dlo', 'list', '-o', orgAlias],
      },
      harmonize: {
        dmos: ['data360', 'dmo', 'list', '-o', orgAlias],
        identityResolution: ['data360', 'identity-resolution', 'list', '-o', orgAlias],
      },
      segment: {
        segments: ['data360', 'segment', 'list', '-o', orgAlias],
        calculatedInsights: ['data360', 'calculated-insight', 'list', '-o', orgAlias],
      },
      act: {
        activationPlatforms: ['data360', 'activation', 'platforms', '-o', orgAlias],
        activationTargets: ['data360', 'activation-target', 'list', '-o', orgAlias],
        dataActionTargets: ['data360', 'data-action-target', 'list', '-o', orgAlias],
      },
      retrieve: {
        searchIndexes: ['data360', 'search-index', 'list', '-o', orgAlias],
        queryDescribe: describeTable
          ? ['data360', 'query', 'describe', '-o', orgAlias, '--table', describeTable]
          : null,
      },
    },
  };
}

function printTextReport(report) {
  const lines = [];
  lines.push(`Data Cloud readiness for ${report.org.alias}`);
  lines.push(`Runtime: ${report.runtime.state}`);
  if (report.runtime.message) lines.push(`  ${report.runtime.message}`);
  lines.push(`Org auth: ${report.org.state}`);
  if (report.org.username) lines.push(`  User: ${report.org.username}`);
  if (report.org.instanceUrl) lines.push(`  Instance: ${report.org.instanceUrl}`);
  lines.push('');
  lines.push('Core probes:');
  for (const [name, probe] of Object.entries(report.core)) {
    lines.push(`  - ${name}: ${probe.state}${probe.count !== null && probe.count !== undefined ? ` (${probe.count})` : ''}`);
    if (probe.code) lines.push(`      code: ${probe.code}`);
    if (probe.message) lines.push(`      ${probe.message}`);
  }
  lines.push('');
  lines.push('Phase readiness:');
  for (const [phase, entry] of Object.entries(report.phases)) {
    lines.push(`  ${phase}: ${entry.summary}`);
    for (const [name, probe] of Object.entries(entry.checks)) {
      lines.push(`    - ${name}: ${probe.state}${probe.count !== null && probe.count !== undefined ? ` (${probe.count})` : ''}`);
      if (probe.code) lines.push(`        code: ${probe.code}`);
      if (probe.message) lines.push(`        ${probe.message}`);
    }
  }
  lines.push('');
  lines.push('Caveats:');
  for (const caveat of report.caveats) {
    lines.push(`  - ${caveat}`);
  }
  lines.push('');
  lines.push('Guidance:');
  if (report.guidance.length === 0) {
    lines.push('  - No blocking issues detected from the chosen probes. Continue with read-only inspection, then mutate intentionally.');
  } else {
    for (const item of report.guidance) {
      lines.push(`  - ${item}`);
    }
  }
  console.log(lines.join('\n'));
}

function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(error.message);
    console.error('');
    console.error(HELP);
    process.exit(1);
  }

  if (args.help) {
    console.log(HELP);
    process.exit(0);
  }

  if (!args.targetOrg) {
    console.error('Missing required --target-org / -o argument.');
    console.error('');
    console.error(HELP);
    process.exit(1);
  }

  const runtimeCheck = runCommand('sf', ['data360', 'man'], { json: false, timeoutSeconds: args.timeout });
  const runtime = runtimeCheck.exitCode === 0
    ? { state: 'ok', command: runtimeCheck.command }
    : { ...classifyError(runtimeCheck.stderr || runtimeCheck.stdout || runtimeCheck.errorMessage || 'sf data360 runtime is unavailable'), command: runtimeCheck.command };

  const orgDisplay = parseOrgDisplay(
    runCommand('sf', ['org', 'display', '-o', args.targetOrg], { json: true, timeoutSeconds: args.timeout }),
    args.targetOrg
  );

  const matrix = buildProbeMatrix(args.targetOrg, args.describeTable);
  const report = {
    runtime,
    org: orgDisplay,
    core: {},
    phases: {},
    caveats: [...CAVEATS],
    guidance: [],
  };

  if (runtime.state !== 'ok' || orgDisplay.state !== 'ok') {
    report.guidance.push(...guidanceFromProbe('runtime', runtime));
    if (orgDisplay.state !== 'ok') {
      report.guidance.push(`Authenticate the target org first: sf org login web -a ${args.targetOrg}`);
    }
    if (args.json) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      printTextReport(report);
    }
    process.exit(runtime.state === 'ok' && orgDisplay.state === 'ok' ? 0 : 1);
  }

  for (const [name, commandArgs] of Object.entries(matrix.core)) {
    report.core[name] = normalizeProbe(name, runCommand('sf', commandArgs, { json: true, timeoutSeconds: args.timeout }));
  }

  const selectedPhases = args.phase === 'all'
    ? Object.keys(matrix.phases)
    : [args.phase];

  for (const phase of selectedPhases) {
    const checks = {};
    const phaseMatrix = matrix.phases[phase] || {};
    for (const [name, commandArgs] of Object.entries(phaseMatrix)) {
      if (!commandArgs) {
        checks[name] = { name, state: 'skipped', reason: 'No describe table was supplied for the query probe.' };
        continue;
      }
      checks[name] = normalizeProbe(name, runCommand('sf', commandArgs, { json: true, timeoutSeconds: args.timeout }));
    }
    report.phases[phase] = {
      summary: summarizePhase(checks),
      checks,
    };
  }

  const uniqueGuidance = new Set();
  for (const [name, probe] of Object.entries(report.core)) {
    for (const item of guidanceFromProbe(`core.${name}`, probe)) uniqueGuidance.add(item);
  }
  for (const [phase, entry] of Object.entries(report.phases)) {
    for (const [name, probe] of Object.entries(entry.checks)) {
      for (const item of guidanceFromProbe(`${phase}.${name}`, probe)) uniqueGuidance.add(item);
    }
  }

  const coreSignals = Object.values(report.core).map((probe) => probe.state);
  if (coreSignals.some((state) => ['ok', 'enabled_empty', 'enabled_populated'].includes(state))) {
    uniqueGuidance.add('At least one core Data Cloud probe succeeded. Treat individual query or feature-gate failures as scoped issues, not automatic proof that the whole product is disabled.');
  }
  uniqueGuidance.add('For core provisioning, tenant creation, or license assignment gaps, use Setup → Data Cloud Setup and the current standard Data Cloud permission sets. Feature Manager can expose some org-specific toggles, but it is not the source of truth for every missing capability.');
  uniqueGuidance.add('Reference: skills/orchestrating-datacloud/references/feature-readiness.md');

  report.guidance = [...uniqueGuidance];

  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    printTextReport(report);
  }

  process.exit(0);
}

main();
