#!/usr/bin/env node
// Deterministic renderer for the Fulfiller-agent create/activate report.
//
// Composing the report from phase state in model prose is unreliable
// (authoring standard A9) — the layout, field placement, and next-step
// wording all belong in a script that emits byte-identical output for a
// given state input. This helper is the single source of report text for
// both the chat-turn response and the harness's ${outputDir}/report.md
// file, so the two never diverge.
//
// Usage:
//   node render-report.mjs <state.json> [outPath]
//
// state.json shape (all fields optional except `verdict`):
//   {
//     "org":            string,
//     "developerName":  string,
//     "label":          string,
//     "preflight":      { "studioHasAccess": "true" | "false" | "cannot-confirm",
//                         "templateAgentScriptPresent": "yes" | "no" | "pending" },
//     "enumerate":      { "existsBeforeWrite": "yes" | "no" | "pending",
//                         "latestVersionStatus": "Active" | "Inactive" | "n/a" | "pending" },
//     "confirmToWrite": "true" | "false" | "pending",
//     "createBundle":   string,
//     "publish":        string,
//     "activate":       string,
//     "verify":         string,
//     "verdict":        "CREATED" | "ALREADY-CREATED" | "ACTIVATED" |
//                       "PENDING CONFIRMATION" | "DECLINED" | "FAILED",
//     "reason":         string
//   }
//
// If `outPath` is provided, writes to that path; otherwise emits to stdout.
// The rendered report is always ~30 lines and shape-identical run to run.

import { readFileSync, writeFileSync } from 'node:fs';

const [statePath, outPath] = process.argv.slice(2);
if (!statePath) {
  process.stderr.write('usage: node render-report.mjs <state.json> [outPath]\n');
  process.exit(2);
}

let state;
try {
  state = JSON.parse(readFileSync(statePath, 'utf8'));
} catch (err) {
  process.stderr.write(`error: could not read/parse ${statePath}: ${err.message}\n`);
  process.exit(3);
}

const VALID_VERDICTS = new Set([
  'CREATED', 'ALREADY-CREATED', 'ACTIVATED',
  'PENDING CONFIRMATION', 'DECLINED', 'FAILED',
]);
const verdict = String(state?.verdict ?? '').trim();
if (!VALID_VERDICTS.has(verdict)) {
  process.stderr.write(`error: verdict "${verdict}" is not one of: ${[...VALID_VERDICTS].join(', ')}\n`);
  process.exit(3);
}

function field(v, fallback = 'pending') {
  const s = v === undefined || v === null ? '' : String(v).trim();
  return s === '' ? fallback : s;
}

const org = field(state.org, '<unspecified>');
const devName = field(state.developerName, '<pending>');
const label = field(state.label, '<pending>');

const preStudio = field(state?.preflight?.studioHasAccess, 'pending');
const preTmpl = field(state?.preflight?.templateAgentScriptPresent, 'pending');
const enumExists = field(state?.enumerate?.existsBeforeWrite, 'pending');
const enumVer = field(state?.enumerate?.latestVersionStatus, 'pending');

function classifyPreflightVerdict() {
  const explicit = field(state?.preflight?.verdict, '');
  if (explicit !== 'pending' && explicit !== '') return explicit;
  if (preStudio === 'false' || preTmpl === 'no') return 'NOT-READY';
  const okStudio = preStudio === 'true';
  const okTmpl = preTmpl === 'yes';
  if (okStudio && okTmpl) return 'READY';
  if (preStudio === 'cannot-confirm' || preTmpl === 'pending') return 'CANNOT-CONFIRM';
  return 'pending';
}
function classifyEnumerate() {
  const explicit = field(state?.enumerate?.verdict, '');
  if (explicit !== 'pending' && explicit !== '') return explicit;
  if (enumExists === 'yes') {
    if (enumVer === 'Active') return 'exists:true, needsActivation:false';
    if (enumVer === 'Inactive') return 'exists:true, needsActivation:true';
    return 'exists:true';
  }
  if (enumExists === 'no') return 'exists:false';
  return 'pending';
}
const preVerdict = classifyPreflightVerdict();
const enumVerdict = classifyEnumerate();

const confirm = field(state.confirmToWrite, 'pending');
const isPending = verdict === 'PENDING CONFIRMATION';
const isDeclined = verdict === 'DECLINED';
const isCreated = verdict === 'CREATED';
const isActivated = verdict === 'ACTIVATED';
const isAlready = verdict === 'ALREADY-CREATED';
const isFailed = verdict === 'FAILED';
const gatedFallback = isPending
  ? 'pending confirmation'
  : isDeclined ? 'skipped'
  : isAlready ? 'skipped (already exists)'
  : isFailed ? 'skipped'
  : 'pending';

const bundleVersionId = field(state.bundleVersionId, '');
const bundleVersionIdSuffix = bundleVersionId ? ` bundleVersionId=${bundleVersionId}` : '';
const onBundleVersionId = bundleVersionId ? ` on bundleVersionId=${bundleVersionId}` : '';

function withCreateSuffix(base) {
  if (base === 'pending' || base.startsWith('skipped') || base === 'pending confirmation') return base;
  return `${base}${bundleVersionIdSuffix}`;
}
function withPublishActivateSuffix(base) {
  if (base === 'pending' || base.startsWith('skipped') || base === 'pending confirmation') return base;
  return `${base}${onBundleVersionId}`;
}

const createBundle = withCreateSuffix(field(state.createBundle, gatedFallback));
const publish = withPublishActivateSuffix(field(state.publish, gatedFallback));
const activate = withPublishActivateSuffix(field(state.activate, gatedFallback));
const verifyFallback = isDeclined || isPending || isFailed
  ? 'skipped'
  : isAlready
    ? `exists:true; latestVersionStatus=${enumVer}`
    : 'pending';
let verify = field(state.verify, verifyFallback);
if (
  (isCreated || isActivated) &&
  verify !== 'pending' &&
  !verify.startsWith('skipped') &&
  !/exists\s*[:=]/i.test(verify)
) {
  verify = `${verify}; exists:true; latestVersionStatus=Active`;
}

const reason = String(state.reason ?? '').trim();

const NEXT_STEPS = {
  'CREATED':
    'The IT Service Fulfiller agent is live as an NGA-native agent (no external-link icon in Agentforce Studio). No new agent was provisioned beyond the one just created. Verify end-to-end in Agentforce Studio\'s Agents list.',
  'ALREADY-CREATED':
    'The IT Service Fulfiller agent was already present and active — no new agent was provisioned. Verify end-to-end in Agentforce Studio\'s Agents list.',
  'ACTIVATED':
    'The existing IT Service Fulfiller agent was found inactive and has been activated — no new agent was provisioned. Verify end-to-end in Agentforce Studio\'s Agents list.',
  'PENDING CONFIRMATION':
    'The run is paused at the confirm-to-write gate. In this skill, create + publish + activate happen as one atomic sequence gated by a single confirmation — there is no supported create-only or publish-without-activate mode, and no partial "create-only" mode of any kind. Re-run and reply "yes" when you are ready for the agent to go live.',
  'DECLINED':
    'No write occurred. This skill\'s create + publish + activate run as one atomic sequence gated by a single confirmation; there is no supported create-only or publish-without-activate mode, and no partial "create-only" mode of any kind. The user\'s decline (or "hold off on activation") kept the run at the gate. Re-run and confirm when ready for the full sequence.',
  'FAILED':
    reason
      ? `Review the Reason above and remediate. Enablement of missing prerequisites is a Setup-UI/admin action outside this skill's scope — use \`service-itsm-agentic-setup-agentforce-studio-validate\` or \`service-itsm-agentic-setup-agentforce-studio-configure\` to check/enable readiness first. Re-run this skill once the blocker is resolved.`
      : 'Review the observed error and remediate. Enablement of missing prerequisites is a Setup-UI/admin action outside this skill\'s scope — use `service-itsm-agentic-setup-agentforce-studio-validate` or `service-itsm-agentic-setup-agentforce-studio-configure` to check/enable readiness first. Re-run this skill once the blocker is resolved.',
};

const report = `# Fulfiller Agent — Create & Activate

IT Service Fulfiller Agent Creation (via service-itsm-agentic-setup-fulfiller-agent-configure)

Org:      ${org} (API v67.0)
Agent:    ${devName} ("${label}") — NGA-native bundle

  Preflight  ......................... Studio hasAccess=${preStudio}; template agentScript present=${preTmpl}; verdict=${preVerdict}
  Enumerate  ......................... target agent exists before write=${enumExists}; latest version status=${enumVer}; verdict=${enumVerdict}
  Confirm-to-write ................... user-confirmed=${confirm}${(confirm === 'true' && (devName !== '<pending>' || label !== '<pending>')) ? `; confirmed developerName=${devName}, label="${label}"` : ''}
  Create bundle ...................... ${createBundle}
  Publish ............................ ${publish}
  Activate ........................... ${activate}
  Verify ............................. ${verify}

Verdict: ${verdict}
Reason:  ${reason}

Next steps:
  - ${NEXT_STEPS[verdict]}
`;

if (outPath) {
  writeFileSync(outPath, report, 'utf8');
  process.stdout.write(outPath + '\n');
} else {
  process.stdout.write(report);
}
