#!/usr/bin/env node
// Strip the Release Management subagent from the decoded Fulfiller Agent Script.
//
// WHY: the shipped ITSM Fulfiller template ships a `topic
// ReleaseManagement:` subagent whose only action, `SummarizeRelease`, is sourced
// from the `svc_itsm_intelligence__SummarizeRelease` invocable. That invocable is
// gated behind Release Management (the `ReleaseManagementPref` org preference /
// `ReleaseManagerPermSet`) and is NOT surfaced by
// `/actions/custom/generatePromptResponse` on an org that has not enabled it. When
// the Agent Script references an unsurfaced action, `activate` returns HTTP 200
// with a `{success:false, "... does not exist"}` silent-failure body and the agent
// never comes up. Rather than force every Fulfiller install to also flip on
// Release Management, the approved workaround is to remove the Release Management
// subagent entirely from the script we create the agent from — the Fulfiller agent
// then activates cleanly on any Agentforce-for-IT-Service org without the pref.
//
// The removal is deliberately COMPLETE — leaving the `go_to_ReleaseManagement`
// transition behind would dangle a `@topic.ReleaseManagement` reference to a topic
// that no longer exists. Three surfaces are removed:
//   1. the top-level `topic ReleaseManagement:` block (carries the SummarizeRelease
//      action's `source:`/`target:` — the actual dependency);
//   2. the `go_to_ReleaseManagement:` transition + its description inside
//      `start_agent topic_selector:` (would otherwise dangle);
//   3. the "- Route to ReleaseManagement ..." routing bullet in the selector's
//      reasoning instructions (cosmetic, but part of a complete removal).
//
// The function operates on the ALREADY-DECODED Agent Script text (post
// HTML-entity decode). It is a no-op — returns the input unchanged with
// `removed.topic === 0` — if no `topic ReleaseManagement:` block is present, so it
// is safe to call unconditionally and against future template revisions.
//
// This module is imported by both `build-create-body.mjs` (the create body must
// not reference the gated action) and `classify-action-availability.mjs` (the
// Phase-2c gate must scan the SAME post-strip script, otherwise it would still
// flag SummarizeRelease as "missing" and block the very flow this strip
// unblocks). The two callers MUST stay in lock-step; both the entity decode
// (`decodeAgentScriptEntities`) and the strip (`stripReleaseManagement`) live
// here and are imported by both callers, so the shipped script and the scanned
// script are byte-identical up to and including the transform.

// ── Shared HTML-entity decoder ──────────────────────────────────────────────
// The `agentScript` arrives HTML-entity-encoded (sometimes double-encoded).
// BOTH callers — build-create-body.mjs (ships the bundle) and
// classify-action-availability.mjs (scans it) — MUST decode it identically
// before the strip runs, or the scanned script and the shipped script can
// diverge on an entity one decoder handles and the other doesn't (e.g. hex
// `&#x27;`, `&apos;`, `&nbsp;`), reintroducing exactly the alias/target
// divergence the shared strip exists to prevent. Keeping ONE decoder here,
// alongside the strip, makes both callers byte-identical up to AND including
// the transform — not just for the strip step.
const NAMED_ENTITIES = { amp: '&', quot: '"', apos: "'", lt: '<', gt: '>', '#39': "'", nbsp: ' ' };
function decodeEntitiesOnce(s) {
  return s.replace(/&(#?\w+);/g, (m, ref) => {
    if (ref.startsWith('#')) {
      const n = ref[1] === 'x' || ref[1] === 'X' ? parseInt(ref.slice(2), 16) : parseInt(ref.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : m;
    }
    return Object.prototype.hasOwnProperty.call(NAMED_ENTITIES, ref) ? NAMED_ENTITIES[ref] : m;
  });
}

/**
 * Fully decode HTML entities in a template `agentScript`, unwinding multi-level
 * encoding by re-running until the text stabilises. Shared by
 * build-create-body.mjs and classify-action-availability.mjs so the shipped and
 * scanned scripts are decoded identically.
 * @param {string} text encoded agentScript
 * @returns {string} decoded text
 */
export function decodeAgentScriptEntities(text) {
  let prev = String(text);
  let next = decodeEntitiesOnce(prev);
  while (next !== prev) { prev = next; next = decodeEntitiesOnce(next); }
  return next;
}

// The `topic ReleaseManagement:` block ends at the next TOP-LEVEL section — a
// non-blank line beginning in column 0. Top-level Agent Script keys are never
// indented; a topic block's contents always are. Detecting the boundary by
// column-0 position rather than by enumerating known section keywords
// (`topic `/`start_agent `/`system:`/…) means a template revision that adds or
// reorders a top-level key — a global `actions:` manifest, a trailing
// `description:`, any new DSL key — still bounds the block correctly instead of
// letting the scan run to EOF and swallow that trailing content. Blank lines
// never bound the block (they read as block-internal).
const isTopLevelBoundary = (l) => /^\S/.test(l);

/**
 * Remove the Release Management subagent from a decoded Fulfiller Agent Script.
 * @param {string} scriptText decoded (post-HTML-entity) Agent Script YAML text
 * @returns {{ text: string, removed: { topic: number, goto: number, bullet: number, residual: number } }}
 *   `removed.residual` is the count of ReleaseManagement/SummarizeRelease tokens
 *   that survive in the stripped text — a non-zero value means the template
 *   references the gated action outside the three stripped surfaces and the
 *   caller should warn (see completeness guard below).
 */
export function stripReleaseManagement(scriptText) {
  const lines = String(scriptText).split(/\r?\n/);
  const out = [];
  const removed = { topic: 0, goto: 0, bullet: 0 };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];

    // 1) Top-level `topic ReleaseManagement:` block — runs until the next
    //    top-level section or EOF.
    if (/^topic\s+ReleaseManagement\s*:/.test(line)) {
      let j = i + 1;
      while (j < lines.length && !isTopLevelBoundary(lines[j])) j += 1;
      removed.topic += j - i;
      i = j - 1; // resume at the next top-level section (or EOF)
      continue;
    }

    // 2) Indented `go_to_ReleaseManagement:` transition block inside the topic
    //    selector — the header line plus every following line more-indented than
    //    it (its `description:` child). Stops at the first non-blank sibling
    //    (indent <= the header's indent).
    const gotoMatch = /^(\s*)go_to_ReleaseManagement\s*:/.exec(line);
    if (gotoMatch) {
      const baseIndent = gotoMatch[1].length;
      let j = i + 1;
      while (j < lines.length) {
        if (lines[j].trim() === '') {
          // Blank line: only part of the block if the next non-blank line is
          // deeper than the header; otherwise the block has ended.
          let k = j;
          while (k < lines.length && lines[k].trim() === '') k += 1;
          if (k >= lines.length) { j = k; break; }
          if (lines[k].match(/^\s*/)[0].length <= baseIndent) break;
          j = k;
          continue;
        }
        if (lines[j].match(/^\s*/)[0].length <= baseIndent) break;
        j += 1;
      }
      removed.goto += j - i;
      i = j - 1;
      continue;
    }

    // 3) Routing bullet naming ReleaseManagement in the selector's reasoning
    //    instructions block scalar.
    if (/^\s*-\s*Route to ReleaseManagement\b/.test(line)) {
      removed.bullet += 1;
      continue;
    }

    out.push(line);
  }

  const text = out.join('\n');
  // Completeness guard: the strip removes three KNOWN
  // surfaces (topic block, go_to transition, routing bullet). If a future
  // template references ReleaseManagement / SummarizeRelease from somewhere else
  // — a global action registry, a variable, a start_agent action list — that
  // reference dangles and reintroduces the {success:false} activate body the
  // strip exists to prevent. Count any survivor so callers can warn rather than
  // silently ship (or scan) a half-stripped script.
  removed.residual = (text.match(/ReleaseManagement|SummarizeRelease/g) || []).length;
  return { text, removed };
}

// CLI shim for debugging: `node strip-release-management.mjs <decoded-script.yaml>`
// prints the stripped script to stdout and the removal counts to stderr.
if (import.meta.url === `file://${process.argv[1]}`) {
  const { readFileSync } = await import('node:fs');
  const path = process.argv[2];
  if (!path) {
    process.stderr.write('usage: node strip-release-management.mjs <decoded-script.yaml>\n');
    process.exit(2);
  }
  const { text, removed } = stripReleaseManagement(readFileSync(path, 'utf8'));
  process.stderr.write(`removed ${JSON.stringify(removed)}\n`);
  process.stdout.write(text);
}
