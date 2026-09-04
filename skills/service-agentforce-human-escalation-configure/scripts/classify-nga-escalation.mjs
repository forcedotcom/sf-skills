#!/usr/bin/env node
// Classify the escalation surface of a retrieved next-gen (AiAuthoringBundle) agent -> { agentType, connectionMessaging, escalateActionPresent, createRecordActionPresent, escalationSurfacePresent, bundleFound }. Detection rules + Service-vs-Employee rationale: references/nga-escalation.md. Exit 3 on an unreadable dir.
//
// Hardening (avoids false CONFIGURED): only actual Agent Script (.agent files, or any file whose
// content declares `start_agent`) is scanned; comments are stripped; and the escalation surface must
// live in the SAME agent block as its trigger, under a `reasoning: actions:` section - a comment,
// example, or unrelated file can no longer satisfy the match. When reachability cannot be proven the
// surface is reported absent (escalationSurfacePresent:false) so the caller stays INCOMPLETE.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const [retrieveDir] = process.argv.slice(2);
if (!retrieveDir) {
  process.stderr.write('usage: node classify-nga-escalation.mjs <retrieve-dir>\n');
  process.exit(2);
}

// The TOP dir must be readable — an unreadable/missing retrieve dir is inconclusive, not "no surface"
// (file contract: exit 3). Nested unreadable files are skipped below (a single bad file is not fatal).
try {
  if (!statSync(retrieveDir).isDirectory()) throw new Error('not a directory');
  readdirSync(retrieveDir);
} catch {
  process.stderr.write(`error: could not read ${retrieveDir}\n`);
  process.exit(3);
}

// Strip comments so a commented-out / example escalation block cannot satisfy the regex: remove
// /* ... */ blocks, then drop whole-line // and # comments (leaves inline // inside strings alone).
function stripComments(text) {
  const noBlock = text.replace(/\/\*[\s\S]*?\*\//g, '');
  return noBlock
    .split('\n')
    .map((line) => {
      const t = line.trimStart();
      return t.startsWith('//') || t.startsWith('#') ? '' : line;
    })
    .join('\n');
}

// Walk the retrieve dir in-process (no `find`; the sandbox blocks find -exec's ARG_MAX probe) and
// collect ONLY Agent Script: files named *.agent, or any file whose content declares `start_agent`
// (covers a differently-named script). bundleFound also counts *.bundle-meta.xml so a bundle with no
// readable script still reports bundleFound:true (→ agentType resolvable, surface simply absent).
function collect(dir, acc) {
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return acc;
  }
  for (const name of entries) {
    const full = join(dir, name);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (st.isDirectory()) {
      collect(full, acc);
      continue;
    }
    if (!st.isFile()) continue;
    const isAgentExt = /\.agent$/i.test(name);
    if (isAgentExt || /\.bundle-meta\.xml$/i.test(name)) acc.bundleFound = true;
    let raw;
    try {
      raw = readFileSync(full, 'utf8');
    } catch {
      continue; // skip unreadable/binary file
    }
    if (isAgentExt || /^[ \t]*start_agent\b/im.test(raw)) {
      acc.scripts.push(stripComments(raw));
    }
  }
  return acc;
}

const scanned = collect(retrieveDir, { scripts: [], bundleFound: false });

// Split concatenated Agent Script into per-agent blocks. Each `start_agent <name>:` opens a block that
// runs until the next start_agent (or EOF). Reachability is proven per block, not across the file.
function splitAgentBlocks(scriptText) {
  const blocks = [];
  let cur = null;
  for (const line of scriptText.split('\n')) {
    if (/^\s*start_agent\b/i.test(line)) {
      if (cur) blocks.push(cur);
      cur = [line];
    } else if (cur) {
      cur.push(line);
    }
  }
  if (cur) blocks.push(cur);
  return blocks;
}

// True when `re` matches an action line inside a `reasoning: actions:` section of the block — i.e. the
// match is more indented than the `actions:` header it lives under (a real action, not prose/an example).
function actionMatches(blockLines, re) {
  let actionsIndent = -1;
  for (const line of blockLines) {
    if (line.trim() === '') continue;
    const indent = line.length - line.trimStart().length;
    if (actionsIndent >= 0) {
      if (indent > actionsIndent) {
        if (re.test(line)) return true;
        continue;
      }
      actionsIndent = -1; // dedented out of the actions section; re-check this line as a new header
    }
    if (/^actions\s*:/.test(line.trim())) actionsIndent = indent;
  }
  return false;
}

const CREATE_RECORD_RE =
  /@actions\.[A-Za-z0-9_]*create[A-Za-z0-9_]*(case|incident|ticket|record)|create[_-]?(case|incident|ticket)\b/i;
const ESCALATE_RE = /@utils\.escalate\b/i;
const MESSAGING_RE = /^\s*connection\s+messaging\s*:/im;

let connectionMessaging = false;
let escalateActionPresent = false;
let createRecordActionPresent = false;
let serviceSurface = false; // messaging + reachable @utils.escalate in the SAME block
let employeeSurface = false; // no messaging + reachable create-record action in the block

for (const script of scanned.scripts) {
  for (const block of splitAgentBlocks(script)) {
    const text = block.join('\n');
    const hasMessaging = MESSAGING_RE.test(text);
    const hasEscalate = actionMatches(block, ESCALATE_RE);
    const hasCreateRecord = actionMatches(block, CREATE_RECORD_RE);
    connectionMessaging = connectionMessaging || hasMessaging;
    escalateActionPresent = escalateActionPresent || hasEscalate;
    createRecordActionPresent = createRecordActionPresent || hasCreateRecord;
    if (hasMessaging && hasEscalate) serviceSurface = true;
    if (!hasMessaging && hasCreateRecord) employeeSurface = true;
  }
}

// Service agents escalate via @utils.escalate; Employee agents lack messaging and must create a
// routable record instead. Without a retrieved bundle the type is unknown.
let agentType = 'unknown';
if (scanned.bundleFound) agentType = connectionMessaging ? 'service' : 'employee';

let escalationSurfacePresent = false;
if (agentType === 'service') escalationSurfacePresent = serviceSurface;
else if (agentType === 'employee') escalationSurfacePresent = employeeSurface;

process.stdout.write(
  JSON.stringify(
    {
      agentType,
      bundleFound: scanned.bundleFound,
      connectionMessaging,
      escalateActionPresent,
      createRecordActionPresent,
      escalationSurfacePresent,
    },
    null,
    2,
  ) + '\n',
);
