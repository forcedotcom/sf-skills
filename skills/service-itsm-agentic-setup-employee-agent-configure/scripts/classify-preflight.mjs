#!/usr/bin/env node
// Deterministic preflight classifier for the Employee-agent create flow.
//
// Two fixed JSON-parsing / decision rules that must not live in model prose
// (authoring standard A9):
//   1. Studio access: read `hasAccess` from the agentforce-studio/access/Agents
//      body → PASS (true) / FAIL (false) / CANNOT-CONFIRM (404 / not wired).
//   2. Template provisioning: find the agent-templates item whose masterLabel
//      matches the target ("IT Service Employee"), confirm it carries a non-empty
//      `agentScript` (the Agent Script YAML fed into the NGA bundle create) → PRESENT
//      (+hasAgentScript) / ABSENT (empty data[] or no match) / CANNOT-CONFIRM
//      (404 / not wired).
//
// Usage:
//   node classify-preflight.mjs <studio-access.json> <agent-templates.json> <masterLabel>
//
// Both file args are paths to raw `sf api request rest` stdout captures; the
// files may hold a Connect error array or be empty when the CLI exited non-zero.
// <masterLabel> is the template's display label (default "IT Service Employee").
//
// Emits a single JSON object to stdout:
//   { studio: { hasAccess, signal, reason },
//     template: { present, id, hasAgentScript, botDefinitionId, signal, reason },
//     verdict, reasons: [...] }
// `botDefinitionId` is copied from the matched agent-templates row and passed to
// the Phase-2 idempotency read as the PRIMARY key (the platform's authoritative
// template→BotDefinition link); the collected developerName is the FALLBACK key
// there. See classify-agent-existence.mjs for why. (The template row's
// `isInstalled`/`isActivated` flags are NOT emitted: they ride the same
// AgentTemplate join as botDefinitionId, so for agents this skill creates — which
// never stamp `templateName` — they read false even after the agent exists, and
// nothing downstream consumes them.)
// where signal is PASS | FAIL | CANNOT-CONFIRM | ERROR and verdict is
// READY | NOT-READY | CANNOT-CONFIRM | ERROR. Exit is always 0 on usable args.
// ERROR (studio only) means the Studio-access read returned a parseable but
// non-404 error body (401/403/unexpected) — that is a failed prerequisite
// read, not an unwired gate, so it must stop the workflow rather than fall
// through to a CANNOT-CONFIRM that a present template can outrun to READY.

import { readFileSync } from 'node:fs';

function readJson(path) {
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false };
    return { ok: true, data: JSON.parse(text) };
  } catch {
    return { ok: false };
  }
}

function asErrorArray(data) {
  if (Array.isArray(data)) return data.filter((e) => e && (e.errorCode || e.message));
  if (data && (data.errorCode || data.message)) return [data];
  return [];
}

function isNotFoundError(data) {
  return asErrorArray(data).some((e) => {
    const code = String(e?.errorCode ?? '').toUpperCase();
    const msg = String(e?.message ?? '').toUpperCase();
    return code.includes('NOT_FOUND') || code.includes('NOT_EXIST') ||
      msg.includes('NOT FOUND') || msg.includes('DOES NOT EXIST') ||
      msg.includes('COULD NOT BE FOUND');
  });
}

function errorSnippet(errs) {
  return errs.map((e) => `${e.errorCode ?? 'ERROR'}: ${e.message ?? ''}`.trim()).join(' | ').slice(0, 500);
}

function classifyStudio(res) {
  if (!res.ok) {
    return { hasAccess: null, signal: 'CANNOT-CONFIRM', reason: 'Studio access — no readable body (endpoint not wired / empty). A successful create/publish/activate is authoritative.' };
  }
  const d = res.data;
  const errs = asErrorArray(d);
  if (errs.length) {
    if (isNotFoundError(d)) return { hasAccess: null, signal: 'CANNOT-CONFIRM', reason: 'Studio access → 404 (access-check gate not wired on this org). Treat as cannot-confirm; a successful create/publish/activate is authoritative.' };
    return { hasAccess: null, signal: 'ERROR', reason: `Studio access read failed: ${errorSnippet(errs)} — surface the raw response and stop; do not treat as an unwired gate.` };
  }
  if (d?.hasAccess === true) return { hasAccess: true, signal: 'PASS', reason: 'Studio access → hasAccess=true.' };
  if (d?.hasAccess === false) return { hasAccess: false, signal: 'FAIL', reason: 'Studio access → hasAccess=false — offer the prerequisite readiness hand-off before any write.' };
  return { hasAccess: null, signal: 'CANNOT-CONFIRM', reason: 'Studio access body had no boolean hasAccess field.' };
}

function classifyTemplate(res, masterLabel) {
  if (!res.ok) {
    return { present: false, id: null, hasAgentScript: false, signal: 'CANNOT-CONFIRM', reason: 'agent-templates — no readable body (endpoint not wired / empty).' };
  }
  const d = res.data;
  if (asErrorArray(d).length) {
    if (isNotFoundError(d)) return { present: false, id: null, hasAgentScript: false, signal: 'CANNOT-CONFIRM', reason: 'agent-templates → 404 (ITSM Connect namespace not provisioned). Hand off to the readiness check.' };
    return { present: false, id: null, hasAgentScript: false, signal: 'CANNOT-CONFIRM', reason: 'agent-templates read returned an error body — surface it.' };
  }
  const items = Array.isArray(d?.data) ? d.data : null;
  if (!items) return { present: false, id: null, hasAgentScript: false, signal: 'CANNOT-CONFIRM', reason: 'agent-templates had no data[] array (unexpected shape).' };
  // Filter to the only namespace this skill instantiates. The endpoint also
  // returns Fulfiller-side (`svc_itsm_intelligence__*`), Slack, ServiceNow,
  // Runtime Insights, and other-namespace entries — some carry masterLabels
  // that collide with in-namespace entries (e.g. `System Password Reset
  // Assistance` exists in both `svc_emp_intelligence__` and `EmpSvcAgent__`).
  // A `masterLabel`-only match would silently pick whichever appeared first
  // in `data[]`; filtering first pins the choice to the correct namespace.
  const inNamespace = items.filter((it) => typeof it?.id === 'string' && it.id.startsWith('svc_emp_intelligence__'));
  const wanted = String(masterLabel).trim().toLowerCase();
  const match = inNamespace.find((it) => String(it?.masterLabel ?? '').trim().toLowerCase() === wanted);
  if (!match) {
    return {
      present: false, id: null, hasAgentScript: false, signal: 'FAIL',
      reason: items.length === 0
        ? 'agent-templates returned an empty data[] — wrong agentType or the org is not ITSM-provisioned; hand off to the readiness check.'
        : inNamespace.length === 0
          ? `agent-templates returned ${items.length} entries but none under the svc_emp_intelligence__ namespace — the Employee IT Service feature toggles are not provisioned on this org; hand off to the readiness check.`
          : `No svc_emp_intelligence__ template with masterLabel "${masterLabel}" (got: ${inNamespace.map((i) => i?.masterLabel).filter(Boolean).join(', ') || 'none'}). Hand off to the readiness check.`,
    };
  }
  // Idempotency identity carried by the matched row — the platform's own link
  // from this template to the BotDefinition it was instantiated into. A populated
  // botDefinitionId is the reliable idempotency signal for PRE-PROVISIONED agents
  // (see classify-agent-existence.mjs): it means the agent already exists
  // regardless of what DeveloperName this skill would have guessed. Agents this
  // skill creates never stamp `templateName`, so their row's botDefinitionId stays
  // null — the Phase-2 read falls back to a DeveloperName key for that case.
  const botDefinitionId = typeof match.botDefinitionId === 'string' && match.botDefinitionId.trim() ? match.botDefinitionId : null;
  if (!match.agentScript || typeof match.agentScript !== 'string' || !match.agentScript.trim()) {
    return { present: true, id: match.id ?? null, hasAgentScript: false, botDefinitionId, signal: 'CANNOT-CONFIRM', reason: `Matched "${masterLabel}" (id=${match.id}) but it had no agentScript field — the NGA bundle create needs the template's Agent Script content.` };
  }
  return { present: true, id: match.id ?? null, hasAgentScript: true, botDefinitionId, signal: 'PASS', reason: `Template "${masterLabel}" present (id=${match.id}) with a non-empty agentScript${botDefinitionId ? `; already instantiated (botDefinitionId=${botDefinitionId})` : '; not yet instantiated (no botDefinitionId — the Phase-2 read falls back to DeveloperName)'} — feed it to scripts/build-create-body.mjs for the NGA bundle create.` };
}

const [studioPath, templatePath, rawLabel] = process.argv.slice(2);
if (!studioPath || !templatePath) {
  process.stderr.write('usage: node classify-preflight.mjs <studio-access.json> <agent-templates.json> [masterLabel]\n');
  process.exit(2);
}
const masterLabel = rawLabel && rawLabel.trim() ? rawLabel : 'IT Service Employee';

const studio = classifyStudio(readJson(studioPath));
const template = classifyTemplate(readJson(templatePath), masterLabel);

// Verdict: the template MUST be present to create. Studio FALSE blocks (hand-off);
// Studio ERROR (non-404 failed read, e.g. 401/403) blocks — surface it, stop.
// Studio CANNOT-CONFIRM (confirmed 404 gate) does not block — create/publish/activate is authoritative.
let verdict;
if (studio.signal === 'ERROR') verdict = 'ERROR';
else if (studio.signal === 'FAIL' || template.signal === 'FAIL') verdict = 'NOT-READY';
else if (template.signal === 'PASS') verdict = 'READY'; // studio PASS, or unconfirmed via a documented 404 gate — template present is enough to attempt
else verdict = 'CANNOT-CONFIRM';

process.stdout.write(JSON.stringify({
  studio: { hasAccess: studio.hasAccess, signal: studio.signal, reason: studio.reason },
  template: {
    present: template.present,
    id: template.id,
    hasAgentScript: template.hasAgentScript,
    // Idempotency identity (from the matched agent-templates row): the Phase-2
    // read uses botDefinitionId as the PRIMARY key and the collected developerName
    // as the FALLBACK. A populated botDefinitionId is the load-bearing "agent
    // already exists" signal for pre-provisioned agents; null just means this
    // template row was never joined (e.g. a self-created agent) — not "no agent".
    botDefinitionId: template.botDefinitionId ?? null,
    signal: template.signal,
    reason: template.reason,
  },
  verdict,
  reasons: [studio.reason, template.reason],
}, null, 2) + '\n');
