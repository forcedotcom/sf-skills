#!/usr/bin/env node
// Deterministic Metadata-key resolver for automation-sandbox-post-copy-configure.
//
// Encodes the field-name resolution rule that was formerly prose in SKILL.md
// (authoring standard A9). Given (ConfigurationName, ConfigFieldName, current
// Metadata block JSON), returns the exact camelCase key inside .Metadata that
// the PATCH should mutate — or FIELD_MAP_UNKNOWN so the caller aborts the
// entry rather than silently updating the wrong field.
//
// Resolution order:
//   1. Override table: known renames between the customer-facing config
//      shape and the Metadata API shape (e.g.
//      RemoteSiteSettings.RemoteSiteUrl → RemoteProxy.Metadata.url).
//   2. Default: lowercase the first character of the config field name
//      (e.g. EndpointUrl → endpointUrl).
//   3. Existence check: the resolved key MUST be present in the current
//      Metadata block. If absent (and no override matched), emit
//      FIELD_MAP_UNKNOWN — the customer's config drift, not something to
//      guess through.
//
// Usage:
//   node map-metadata-key.mjs <ConfigurationName> <ConfigFieldName> <metadataJsonPath>
//
// Emits to stdout (single JSON object):
//   OK      → { "status": "OK",                 "key": "<resolved>" }
//   Unknown → { "status": "FIELD_MAP_UNKNOWN",  "candidateKey": "<tried>",
//               "availableKeys": [...], "reason": "..." }
//
// Exit code 0 in both cases (the caller inspects status); non-zero only on
// input/parse errors.

import { readFileSync } from 'node:fs';

function fail(msg) {
  process.stderr.write(`map-metadata-key: ${msg}\n`);
  process.exit(1);
}

const [, , configurationName, configFieldName, metaPath] = process.argv;
if (!configurationName || !configFieldName || !metaPath) {
  fail('usage: map-metadata-key.mjs <ConfigurationName> <ConfigFieldName> <metadataJsonPath>');
}

const OVERRIDES = {
  RemoteSiteSettings: {
    RemoteSiteUrl: 'url',
  },
};

function defaultCamelize(name) {
  if (!name) return name;
  return name.charAt(0).toLowerCase() + name.slice(1);
}

const override = OVERRIDES[configurationName]?.[configFieldName];
const candidateKey = override ?? defaultCamelize(configFieldName);
const overrideMatched = Boolean(override);

let currentMeta;
try {
  const raw = readFileSync(metaPath, 'utf-8');
  currentMeta = JSON.parse(raw);
} catch (err) {
  fail(`cannot read/parse metadata JSON at ${metaPath}: ${err.message}`);
}

if (currentMeta === null || typeof currentMeta !== 'object' || Array.isArray(currentMeta)) {
  fail(`metadata JSON at ${metaPath} is not an object`);
}

const availableKeys = Object.keys(currentMeta);
const present = Object.prototype.hasOwnProperty.call(currentMeta, candidateKey);

if (present) {
  process.stdout.write(JSON.stringify({ status: 'OK', key: candidateKey }) + '\n');
  process.exit(0);
}

if (overrideMatched) {
  process.stdout.write(
    JSON.stringify({
      status: 'FIELD_MAP_UNKNOWN',
      candidateKey,
      availableKeys,
      reason: `override "${configurationName}.${configFieldName}" → "${candidateKey}" but that key is not present in the current Metadata block`,
    }) + '\n',
  );
  process.exit(0);
}

process.stdout.write(
  JSON.stringify({
    status: 'FIELD_MAP_UNKNOWN',
    candidateKey,
    availableKeys,
    reason: `default rename "${configFieldName}" → "${candidateKey}" is not a key in the current Metadata block; no override table entry for ${configurationName}.${configFieldName}`,
  }) + '\n',
);
