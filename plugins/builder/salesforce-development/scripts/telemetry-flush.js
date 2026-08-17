#!/usr/bin/env node
/*
 * telemetry-flush.js — Stream B transmitter for the salesforce-development plugin.
 *
 * The Python hooks NEVER touch the network. On session end, `sf-context
 * telemetry-flush` renames the session's own buffer to a private snapshot and spawns
 * a detached Python sender (`telemetry-send`); that sender resolves the org, writes a
 * pending job to .sf/telemetry-pending-<pid>.json, and spawns THIS script detached —
 * so the upload outlives the hook and never blocks it, the same shape as the SF CLI's
 * own detached `plugin-telemetry` uploader.
 *
 * This is a deliberately thin transmitter: all scrubbing, allowlisting, and the
 * event mapping already happened in Python (sf_telemetry.py). Here we only read
 * the pending job (argv[2]), resolve @salesforce/telemetry (+ @salesforce/core for
 * O11y) from the INSTALLED SF CLI's node_modules (the CLI bundles them; we don't
 * vendor our own), and hand the pre-shaped events to the O11y sink:
 *
 *   - O11y leg (job.events + job.a4dEvents): create an O11y-enabled reporter whose
 *     getConnectionFn opens the connected org, so the upload goes through
 *     /services/data/vXX/connect/proxy/ui-telemetry on the org's instance. It
 *     carries TWO event SHAPES on the one transport: the fixed PdpEvent
 *     (job.events, via sendPdpEvent) and the flexible UIP shape (job.a4dEvents, via
 *     sendTelemetryEvent — o11y schema sf_a4dInstrumentation, feeding UIP Hive ->
 *     Tableau). Then flush/stopAsync. Needs job.username (an org).
 *
 * The leg is fail-open: any error just means telemetry didn't send this session.
 * Exit code is always 0 — a telemetry failure must never look like a real error.
 * The pending file is deleted in a finally block (like the CLI uploader) so a
 * transient failure doesn't wedge the buffer or re-send next session.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

// End-to-end deadline (ms) for the O11y sink's whole lifecycle. Overridable via env
// ONLY so tests can exercise the timeout path in ~1s instead of the production
// window; ops never needs to set it. The default bounds the detached process to a
// worst-case ~15s even if the sink stalls, and every override is CLAMPED to
// MAX_DEADLINE_MS so a bogus/huge value can never keep this process alive for
// minutes (a raw Number(env) would let e.g. 2147483647 run cleanup ~24 days out).
const MAX_DEADLINE_MS = 60000;
function deadlineFromEnv(name, dflt) {
  const v = Number(process.env[name]);
  if (!Number.isFinite(v) || v <= 0) return dflt;
  return Math.min(v, MAX_DEADLINE_MS);
}
const O11Y_DEADLINE_MS = deadlineFromEnv('SF_DEV_TELEMETRY_O11Y_DEADLINE_MS', 15000);

// Last-moment opt-out check, mirroring Python's _is_enabled(): the ecosystem
// opt-out env vars always win, else the machine-wide consent file is off iff it
// explicitly says {"enabled": false} (absent/unreadable == default-ON). Python
// checks consent when it queues the job, but the user may run `telemetry off`
// AFTER that — including for a job queued by ANOTHER project, whose pending file
// `telemetry off` cannot reach. Re-reading the machine consent here, right before
// any sink starts, closes that window to sub-second and covers the cross-project
// case: no sink runs once the user has opted out.
function telemetryOptedOut(job) {
  if (process.env.SF_DISABLE_TELEMETRY || process.env.DO_NOT_TRACK) return true;
  const f = job && job.consentFile;
  if (!f) return false; // no path provided — defer to Python's earlier gate
  try {
    const cfg = JSON.parse(fs.readFileSync(f, 'utf8'));
    return !!cfg && cfg.enabled === false;
  } catch {
    return false; // unreadable/absent consent == default-ON
  }
}

// Bound the sink's whole lifecycle (create + send + flush + stop) so a stalled
// network call can never hang this detached process. Resolves (never rejects) when
// the work finishes OR the deadline elapses — the caller awaits it fail-open, so a
// timeout here simply means "telemetry didn't finish this session".
//
// The timer is deliberately NOT unref'd: on a stall with no active handle (a pure
// hang), an unref'd timer would let node's event loop drain and the process would
// exit BEFORE allSettled resolves — skipping the finally that unlinks the pending
// file (verified: bare-Promise hang exits ~40ms, pending left behind). Keeping the
// timer ref'd holds the process alive until the deadline so cleanup always runs;
// we clearTimeout on normal completion so the happy path never waits on it.
function withDeadline(promise, ms) {
  return new Promise((resolve) => {
    let settled = false;
    let timer;
    const done = () => { if (!settled) { settled = true; clearTimeout(timer); resolve(); } };
    timer = setTimeout(done, ms);
    Promise.resolve(promise).then(done, done);
  });
}

// O11y leg: upload both event shapes through the connected org's proxy. Each send
// is individually guarded and flush/stop always run in a finally, so any single
// failure stays contained and the batch still flushes fail-open.
async function sendO11y(TelemetryReporter, Org, job) {
  const events = Array.isArray(job.events) ? job.events : [];
  // UIP flexible format (O11y sf_a4dInstrumentation schema) is a second event SHAPE
  // on this same O11y transport (not a new sink) — emitted below on the SAME
  // reporter/connection/endpoint via sendTelemetryEvent.
  const a4dEvents = Array.isArray(job.a4dEvents) ? job.a4dEvents : [];
  if (!events.length && !a4dEvents.length) return;
  // O11y uploads through the CONNECTED ORG. With no username we can't open a
  // connection, so there's nothing to authenticate the upload against — skip.
  if (!job.username) return;

  // Resolve the org connection ONCE so we can (a) reuse it for the reporter's
  // getConnectionFn and (b) derive the upload endpoint from the org's OWN instance
  // url. The reporter POSTs via connection.requestPost() to the org-relative path;
  // the endpoint below is only the fallback — pointed at the same org host so
  // telemetry can NEVER egress to a non-org domain even on the fallback path. Its
  // pinned vNN is a fallback-only API version (the primary POST is org-relative and
  // unversioned here); bump it when the plugin's minimum Salesforce API version moves.
  const connection = await (await Org.create({ aliasOrUsername: job.username })).getConnection();
  const instanceUrl = connection.instanceUrl || connection.getConnectionOptions?.().instanceUrl;
  if (!instanceUrl) return; // no resolvable org host — do not send anywhere
  const uploadEndpoint = `${instanceUrl.replace(/\/$/, '')}/services/data/v65.0/connect/proxy/ui-telemetry`;

  const reporter = await TelemetryReporter.create({
    project: job.project || 'salesforce-development',
    key: 'not-used',            // AppInsights disabled; O11y needs no key
    userId: job.machineId || undefined,
    waitForConnection: true,
    enableO11y: true,
    enableAppInsights: false,
    o11yUploadEndpoint: uploadEndpoint,   // org-derived; fallback stays on-org
    getConnectionFn: async () => connection,
    o11yBatching: { enableAutoBatching: true, enableShutdownHook: true },
  });

  // The public reporter.sendPdpEvent() is fire-and-forget: internally it runs
  // `void this.o11yReporter.sendPdpEvent(event).catch(...)` and returns
  // synchronously — BEFORE the event's async chain (await init -> await schema ->
  // logEventWithSchema -> O11y collector) has landed the event. A flush/stopAsync
  // right after then sees an EMPTY collector (hasData === false) and uploads
  // nothing. So we await the UNDERLYING o11yReporter.sendPdpEvent, whose promise
  // resolves only once the event is actually in the collector, then flush.
  // (Verified against a live org proxy: messagesReceived === events.length,
  // messagesDropped === 0. The public method drops all.)
  // Last-instant opt-out re-check before the first network send: create() above
  // is async, so re-read here to catch a `telemetry off` that landed mid-
  // construction (narrows the window to ~microseconds; see telemetryOptedOut).
  if (telemetryOptedOut(job)) { try { await reporter.stopAsync(); } catch {} return; }
  const o11y = reporter.o11yReporter;
  // If O11y didn't initialize (init() threw, or the CLI's own telemetry is
  // disabled — see telemetryReporter.js), o11yReporter is undefined. There is NO
  // working fallback: the public reporter.sendPdpEvent() is itself gated on
  // `enableO11y && this.o11yReporter`, so calling it here would silently drop the
  // event while looking like a send. Skip honestly (fail-open) rather than pretend.
  if (!o11y) return;
  // Enqueue both shapes, then ALWAYS flush + stop. Each send is individually
  // guarded and flush/stop run in a finally, so a single failed event — or a
  // rejected UIP send — can never abort the batch: the PDP events already in the
  // collector still upload, the UIP shape is attempted independently, and the
  // reporter is always torn down.
  try {
    for (const event of events) {
      try {
        await o11y.sendPdpEvent(event); // awaits until the event is in the collector
      } catch { /* skip this event; keep the batch */ }
    }
    // UIP shape on the SAME reporter/connection/endpoint: sendTelemetryEvent
    // JSON-serializes the attributes into the UIP `message` field (o11y schema
    // sf_a4dInstrumentation) and delivers through the same org proxy. Each send is
    // guarded so a UIP failure never blocks the PDP events already enqueued above
    // nor the flush below.
    for (const ev of a4dEvents) {
      if (!ev || !ev.eventName) continue;
      try {
        await o11y.sendTelemetryEvent(ev.eventName, ev.attributes || {});
      } catch { /* skip this event; keep the batch */ }
    }
  } finally {
    try { await reporter.flush(); } catch { /* fail-open */ }
    try { await reporter.stopAsync(); } catch { /* fail-open */ }
  }
}

async function main() {
  const pendingPath = process.argv[2];
  if (!pendingPath) return;

  // Everything below is inside the try so the finally ALWAYS unlinks the pending
  // file — even on an unreadable/malformed job or an opt-out short-circuit. A
  // pending file that survives would wedge the buffer or re-send next session.
  try {
    let job;
    try {
      job = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
    } catch {
      return; // nothing readable to send (finally still consumes the file)
    }

    const nodeModules = job.cliNodeModules;
    if (!nodeModules) return; // can't resolve the transport library

    // Resolve the CLI's bundled libraries by path — do NOT rely on this script's
    // own module resolution (it ships in a plugin with no node_modules).
    const cliRequire = createRequire(path.join(nodeModules, 'noop.js'));
    let TelemetryReporter, Org;
    try {
      ({ TelemetryReporter } = cliRequire('@salesforce/telemetry'));
      ({ Org } = cliRequire('@salesforce/core'));
    } catch {
      return; // CLI libraries not present — silently skip transmit
    }

    // Hard opt-out re-check, as the LAST thing before any sink starts (see
    // telemetryOptedOut) — placed after the synchronous module-resolution above so
    // the consent read is immediately adjacent to the network send, closing the
    // window where `telemetry off` lands after the job was queued (incl. a job
    // queued by another project). finally still consumes the pending file.
    if (telemetryOptedOut(job)) return;

    // The single O11y sink, fail-open and bounded by an end-to-end deadline
    // (covering reporter creation, sends, flush, and stop) so it can never hang this
    // detached process forever. withDeadline resolves (never rejects) on completion
    // OR timeout, so a failure/timeout just means telemetry didn't send this session
    // — the finally below still consumes the pending file.
    await withDeadline(sendO11y(TelemetryReporter, Org, job), O11Y_DEADLINE_MS);
  } catch {
    // fail-open: a telemetry error is never surfaced
  } finally {
    // Always consume the pending file so we never re-send or wedge the buffer.
    try {
      fs.unlinkSync(pendingPath);
    } catch {
      /* ignore */
    }
  }
}

main().then(
  () => process.exit(0),
  () => process.exit(0)
);
