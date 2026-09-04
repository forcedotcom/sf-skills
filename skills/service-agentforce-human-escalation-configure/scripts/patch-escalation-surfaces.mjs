#!/usr/bin/env node
// Idempotent in-place patcher for canEscalate + outboundRoute surfaces; refuses (exit 4) if no safe insertion point. XSD order + modes: references/classifier-contracts.md.

import { readFileSync, writeFileSync } from 'node:fs';

const [mode, filePath, flowName, escalationMessageArg] = process.argv.slice(2);
if (!mode || !filePath) {
  process.stderr.write('usage: node patch-escalation-surfaces.mjs <canEscalate|outboundRoute> <file> [flowApiName] [escalationMessage]\n');
  process.exit(2);
}

const xmlEscape = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

let text;
try {
  text = readFileSync(filePath, 'utf8');
} catch {
  process.stderr.write(`error: cannot read ${filePath}\n`);
  process.exit(2);
}

const done = (summary) => { process.stdout.write(JSON.stringify(summary) + '\n'); process.exit(0); };
const refuse = (msg) => { process.stderr.write(`refuse: ${msg}\n`); process.exit(4); };

// Return {index, indent} of the earliest top-level opening tag from `tags` found in `hay`
// (searched from offset `from`), along with the leading whitespace on that tag's line.
const firstTag = (hay, tags, from = 0) => {
  const scope = hay.slice(from);
  let best = null;
  for (const t of tags) {
    const re = new RegExp(`([ \\t]*)<${t}(?=[ >/])`, 'g');
    for (const m of scope.matchAll(re)) {
      const idx = from + m.index;
      if (best === null || idx < best.index) best = { index: idx, indent: m[1] || '' };
      break; // first match of this tag is enough
    }
  }
  return best;
};

if (mode === 'canEscalate') {
  // Idempotent: normalize an existing <canEscalate> to true.
  if (/<canEscalate>[\s\S]*?<\/canEscalate>/.test(text)) {
    const next = text.replace(/<canEscalate>[\s\S]*?<\/canEscalate>/, '<canEscalate>true</canEscalate>');
    if (next !== text) writeFileSync(filePath, next);
    done({ mode, changed: next !== text, action: 'set-existing' });
  }
  const rootOpen = text.match(/<GenAiPlugin\b[^>]*>/);
  if (!rootOpen) refuse('no <GenAiPlugin> root element found');
  let searchFrom = rootOpen.index + rootOpen[0].length;
  // Skip PAST any <aiPluginUtterances> blocks first - they legally precede canEscalate and each
  // one carries a nested <developerName>, which would otherwise be mistaken for the top-level anchor.
  const utteranceCloses = [...text.matchAll(/<\/aiPluginUtterances>/g)];
  if (utteranceCloses.length) {
    const last = utteranceCloses[utteranceCloses.length - 1];
    searchFrom = last.index + '</aiPluginUtterances>'.length;
  }
  // canEscalate must come BEFORE the first of these top-level siblings.
  const anchor = firstTag(text, [
    'description', 'developerName', 'genAiFunctions', 'genAiPluginInstructions',
    'language', 'localActionLinks', 'localActions', 'localDeveloperName',
    'masterLabel', 'pluginType', 'scope', 'source',
  ], searchFrom);
  if (!anchor) refuse('no post-canEscalate sibling (description/developerName/masterLabel/...) found; refusing to guess placement');
  const indent = anchor.indent || '    ';
  const insertion = `${indent}<canEscalate>true</canEscalate>\n`;
  const followingTag = text.slice(anchor.index).match(/<([A-Za-z]+)/)[1];
  const next = text.slice(0, anchor.index) + insertion + text.slice(anchor.index);
  writeFileSync(filePath, next);
  done({ mode, changed: true, action: 'inserted-before-' + followingTag });
}

if (mode === 'outboundRoute') {
  if (!flowName) { process.stderr.write('error: outboundRoute requires <flowApiName>\n'); process.exit(2); }
  const escMsg = xmlEscape(escalationMessageArg || 'Transferring you to a live support agent.');
  const MESSAGING_SURFACES = new Set(['Messaging', 'CustomerWebClient']);

  const surfaces = [...text.matchAll(/<plannerSurfaces>([\s\S]*?)<\/plannerSurfaces>/g)];
  if (surfaces.length === 0) refuse('no <plannerSurfaces> block found; refusing to invent one');
  const chosen = surfaces.find((m) => {
    const t = m[1].match(/<surfaceType>\s*([^<]*?)\s*<\/surfaceType>/);
    return t && MESSAGING_SURFACES.has(t[1].trim());
  });
  if (!chosen) refuse('no Messaging-class planner surface (surfaceType Messaging|CustomerWebClient) found');

  const innerStart = chosen.index + '<plannerSurfaces>'.length;
  const innerEnd = chosen.index + chosen[0].length - '</plannerSurfaces>'.length;
  const inner = text.slice(innerStart, innerEnd);

  // Idempotent: an existing outboundRouteConfigs already targeting this flow -> normalize the type only.
  const existing = [...inner.matchAll(/<outboundRouteConfigs>([\s\S]*?)<\/outboundRouteConfigs>/g)]
    .find((c) => {
      const n = c[1].match(/<outboundRouteName>\s*([^<]*?)\s*<\/outboundRouteName>/);
      return n && n[1].trim() === flowName;
    });
  if (existing) {
    const block = existing[0];
    let newBlock = block;
    if (/<outboundRouteType>[\s\S]*?<\/outboundRouteType>/.test(block)) {
      newBlock = block.replace(/<outboundRouteType>[\s\S]*?<\/outboundRouteType>/, '<outboundRouteType>OmniChannelFlow</outboundRouteType>');
    } else {
      newBlock = block.replace(/<\/outboundRouteConfigs>/, '    <outboundRouteType>OmniChannelFlow</outboundRouteType>\n        </outboundRouteConfigs>');
    }
    if (newBlock === block) done({ mode, changed: false, action: 'already-configured' });
    const newInner = inner.replace(block, newBlock);
    const next = text.slice(0, innerStart) + newInner + text.slice(innerEnd);
    writeFileSync(filePath, next);
    done({ mode, changed: true, action: 'normalized-type' });
  }

  // Insert a fresh block BEFORE <surface> to honor the AiPlannerSurfaceDef XSD sequence
  // (...outboundRouteConfigs*, surface, surfaceType). <surface> is required, so it must be present.
  const surfaceAnchor = firstTag(inner, ['surface']);
  if (!surfaceAnchor) refuse('Messaging planner surface has no <surface> element; refusing to guess insertion point');
  const indent = surfaceAnchor.indent || '        ';
  const childIndent = indent + '    ';
  const block =
    `${indent}<outboundRouteConfigs>\n` +
    `${childIndent}<escalationMessage>${escMsg}</escalationMessage>\n` +
    `${childIndent}<outboundRouteName>${xmlEscape(flowName)}</outboundRouteName>\n` +
    `${childIndent}<outboundRouteType>OmniChannelFlow</outboundRouteType>\n` +
    `${indent}</outboundRouteConfigs>\n`;
  const newInner = inner.slice(0, surfaceAnchor.index) + block + inner.slice(surfaceAnchor.index);
  const next = text.slice(0, innerStart) + newInner + text.slice(innerEnd);
  writeFileSync(filePath, next);
  done({ mode, changed: true, action: 'inserted-before-surface' });
}

process.stderr.write(`error: unknown mode '${mode}'\n`);
process.exit(2);
