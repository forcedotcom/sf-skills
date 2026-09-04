#!/usr/bin/env node
// Extracts outbound-route wiring from a retrieved GenAiPlannerBundle, coupling routeName+routeType within one outboundRouteConfigs block → { name, type, surface, sameBlock, messagingSurface }; exit 2 on bad usage. Details: references/classifier-contracts.md.

import { readFileSync } from 'node:fs';

const [xmlPath, expectedFlow = ''] = process.argv.slice(2);
if (!xmlPath) {
  process.stderr.write('usage: node extract-outbound-route.mjs <bundle-xml-file> <expected-flow-name>\n');
  process.exit(2);
}

const empty = { name: '', type: '', surface: '', sameBlock: false, messagingSurface: false };

let xml = '';
try {
  xml = readFileSync(xmlPath, 'utf8');
} catch {
  process.stdout.write(JSON.stringify(empty) + '\n');
  process.exit(0);
}

const MESSAGING_SURFACES = new Set(['Messaging', 'CustomerWebClient']);
const tag = (block, name) => {
  const m = block.match(new RegExp(`<${name}>\\s*([^<]*?)\\s*</${name}>`, 's'));
  return m ? m[1].trim() : '';
};

// Collect candidate blocks: prefer plannerSurfaces entries (so we know the surfaceType), and
// fall back to bare outboundRouteConfigs blocks if the bundle is flat/uncompiled.
const candidates = [];
for (const sm of xml.matchAll(/<plannerSurfaces>([\s\S]*?)<\/plannerSurfaces>/g)) {
  const surfaceBlock = sm[1];
  const surface = tag(surfaceBlock, 'surfaceType');
  for (const cm of surfaceBlock.matchAll(/<outboundRouteConfigs>([\s\S]*?)<\/outboundRouteConfigs>/g)) {
    candidates.push({ surface, block: cm[1] });
  }
}
if (candidates.length === 0) {
  for (const cm of xml.matchAll(/<outboundRouteConfigs>([\s\S]*?)<\/outboundRouteConfigs>/g)) {
    candidates.push({ surface: '', block: cm[1] });
  }
}

const describe = (c) => {
  const name = tag(c.block, 'outboundRouteName');
  const type = tag(c.block, 'outboundRouteType');
  return {
    name,
    type,
    surface: c.surface,
    sameBlock: name !== '' && type !== '',
    messagingSurface: MESSAGING_SURFACES.has(c.surface),
  };
};

let chosen = null;
if (expectedFlow) {
  chosen = candidates.map(describe).find((d) => d.name === expectedFlow) || null;
}
if (!chosen) {
  chosen = candidates.length ? describe(candidates[0]) : null;
}
if (!chosen) {
  chosen = empty;
}

process.stdout.write(JSON.stringify(chosen) + '\n');
