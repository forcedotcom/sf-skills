#!/usr/bin/env node
// Deterministic verdict from an evidence.json → { verdict, deterministicPass, directivePass, checks[], missing[] }; exit 3 on unparseable. evidence.json contract: references/classifier-contracts.md.

import { readFileSync } from 'node:fs';

const [evidencePath] = process.argv.slice(2);
if (!evidencePath) {
  process.stderr.write('usage: node verify-escalation-config.mjs <evidence.json>\n');
  process.exit(2);
}

let e;
try {
  const text = readFileSync(evidencePath, 'utf8').trim();
  e = text ? JSON.parse(text) : {};
} catch {
  process.stderr.write(`error: could not read/parse ${evidencePath}\n`);
  process.exit(3);
}

const nonEmpty = (v) => typeof v === 'string' && v.trim() !== '';
const flowNamesMatch =
  nonEmpty(e.outboundRouteName) &&
  nonEmpty(e.expectedFlowName) &&
  e.outboundRouteName === e.expectedFlowName;

// The outbound route is only real when the SAME planner-surface block carries a matching
// route name AND an OmniChannelFlow route type, on a Messaging-class surface. A bundle that
// has the right name and an OmniChannelFlow type in unrelated blocks must NOT pass.
const outboundRouteWired =
  flowNamesMatch &&
  e.outboundRouteType === 'OmniChannelFlow' &&
  e.outboundRouteSameBlock === true &&
  e.outboundRouteMessagingSurface === true;

// The routing-infrastructure half is authoring-model-agnostic - it is deterministic in both models.
const routingChecks = [
  { key: 'outboundFlowActive', ok: nonEmpty(e.flowActiveVersionId), kind: 'deterministic' },
  { key: 'humanQueue', ok: nonEmpty(e.queueId), kind: 'deterministic' },
  { key: 'queueSobject', ok: e.queueSobjectPresent === true, kind: 'deterministic' },
  { key: 'queueHasActiveDirectUserMember', ok: e.queueHasActiveDirectUserMember === true, kind: 'deterministic' },
  { key: 'queueRoutingConfig', ok: e.queueRoutingConfigPresent === true, kind: 'deterministic' },
  { key: 'queueRoutingConfigBound', ok: e.queueRoutingConfigBound === true, kind: 'deterministic' },
  { key: 'agentActive', ok: e.agentActive === true, kind: 'deterministic' },
];

// Model-specific agent surface: classic authors canEscalate + a same-block Messaging outboundRoute;
// NGA verifies a reachable @utils.escalate (Service) or create-record (Employee) in the AiAuthoringBundle.
const authoringModel = e.authoringModel === 'nga' ? 'nga' : 'classic';
const surfaceChecks =
  authoringModel === 'nga'
    ? [{ key: 'ngaEscalationSurface', ok: e.ngaEscalationSurfacePresent === true, kind: 'deterministic' }]
    : [
        { key: 'canEscalate', ok: e.canEscalate === true, kind: 'deterministic' },
        { key: 'outboundRouteConfigs', ok: outboundRouteWired, kind: 'deterministic' },
      ];

const checks = [
  ...surfaceChecks,
  ...routingChecks,
  { key: 'thresholdDirective', ok: e.thresholdAuthored === true, kind: 'directive' },
];

const deterministic = checks.filter((c) => c.kind === 'deterministic');
const deterministicPass = deterministic.every((c) => c.ok);
const directivePass = checks.find((c) => c.key === 'thresholdDirective').ok;
const missing = checks.filter((c) => !c.ok).map((c) => c.key);

const defaultFailureThreshold =
  Number.isInteger(e.defaultFailureThreshold) ? e.defaultFailureThreshold : null;

// A missing failure-threshold directive must NOT read as fully CONFIGURED: routing can be complete
// while the escalation policy (default two-failure / password-reset override) is not yet guaranteed.
// Distinguish the three cases so a policy gap is never hidden behind a green verdict.
const verdict = !deterministicPass
  ? 'INCOMPLETE'
  : directivePass
    ? 'CONFIGURED'
    : 'ROUTING_CONFIGURED_POLICY_PENDING';

process.stdout.write(JSON.stringify({
  verdict,
  authoringModel,
  deterministicPass,
  directivePass,
  defaultFailureThreshold,
  checks,
  missing,
}, null, 2) + '\n');
