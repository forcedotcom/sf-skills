#!/usr/bin/env node
/**
 * Generate oclif.manifest.json for the sf-cli-plugin-data360 community plugin.
 *
 * Why this exists:
 *   `npx oclif manifest` imports every command class, which triggers the
 *   @oclif/core class hierarchy. When the plugin's pinned @oclif/core is
 *   older than what the current Node.js version expects, the import fails
 *   with "Cannot read properties of undefined (reading 'prototype')".
 *
 *   This script avoids importing commands entirely. It walks the compiled
 *   lib/commands/ directory and extracts static metadata from source text
 *   via regex, producing a valid manifest that tells oclif to skip
 *   auto-discovery and auto-transpilation.
 *
 * Usage:
 *   node generate-manifest.mjs            # uses cwd
 *   node generate-manifest.mjs /path/to   # uses explicit plugin root
 */

import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

const pluginRoot = process.argv[2] || process.cwd();
const pkg = JSON.parse(readFileSync(join(pluginRoot, 'package.json'), 'utf8'));
const commandsDir = join(pluginRoot, (pkg.oclif?.commands || './lib/commands').replace('./', ''));

function walk(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) files.push(...walk(full));
    else if (entry.endsWith('.js') && !entry.endsWith('.test.js')) files.push(full);
  }
  return files;
}

function parseCommandSource(source, id) {
  const cmd = { id, pluginName: pkg.name, pluginType: 'link', aliases: [] };

  const summaryMatch = source.match(/static\s+summary\s*=\s*['"`]([^'"`]+)/);
  if (summaryMatch) cmd.summary = summaryMatch[1];

  const descMatch = source.match(/static\s+description\s*=\s*['"`]([^'"`]+)/);
  if (descMatch) cmd.description = descMatch[1];

  if (/static\s+hidden\s*=\s*true/.test(source)) cmd.hidden = true;
  if (/static\s+strict\s*=\s*false/.test(source)) cmd.strict = false;
  if (/static\s+enableJsonFlag\s*=\s*true/.test(source)) cmd.enableJsonFlag = true;

  return cmd;
}

const commands = {};
for (const file of walk(commandsDir)) {
  const rel = relative(commandsDir, file).replace(/\.js$/, '');
  const id = rel.split(sep).join(':');
  try {
    commands[id] = parseCommandSource(readFileSync(file, 'utf8'), id);
  } catch {
    commands[id] = { id, pluginName: pkg.name, pluginType: 'link', aliases: [] };
  }
}

const manifest = { version: pkg.version, commands };
const outPath = join(pluginRoot, 'oclif.manifest.json');
writeFileSync(outPath, JSON.stringify(manifest, null, 2));
console.log(`Generated oclif.manifest.json: ${Object.keys(commands).length} commands (v${pkg.version})`);
