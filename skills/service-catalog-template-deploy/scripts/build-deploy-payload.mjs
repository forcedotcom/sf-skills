#!/usr/bin/env node
// Deterministic deploy-body builder (authoring standard A9).
//
// Transforming templateDependencyMetadata into the deploy POST body's
// flowTemplates[] is a FIXED transformation — iterate dependencies, pick the
// primary key with a defined fallback, and pass enum values through VERBATIM
// (SCREAMING_SNAKE_CASE). Doing it in prose invites the model to normalize
// casing or hardcode a literal, which the live API rejects. This script
// guarantees a consistent body and never mutates enum casing.
//
// Usage:
//   node build-deploy-payload.mjs <resolved.json> [optional-fields.json]
//
// <resolved.json> is a FILE PATH to either:
//   - the object emitted by resolve-template.mjs (its .resolved.templateDependencyMetadata is used), OR
//   - a bare templateDependencyMetadata array, OR
//   - a single template object carrying templateDependencyMetadata.
// [optional-fields.json] is a FILE PATH to a JSON object of user-supplied
// optional keys to merge in (description / isActive / deploymentMode / catalog
// / category / serviceProcessName). Only keys the user actually supplied should
// be present; absent keys are omitted from the body entirely.
//
// Prints the deploy POST body to stdout. Exit 0 on success; exit 2 on bad args.

import { readFileSync } from 'node:fs';

const [resolvedPath, optionalPath] = process.argv.slice(2);
if (!resolvedPath) {
  process.stderr.write('usage: node build-deploy-payload.mjs <resolved.json> [optional-fields.json]\n');
  process.exit(2);
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (err) {
    process.stderr.write(`build-deploy-payload: cannot read/parse ${path}: ${err.message}\n`);
    process.exit(2);
  }
}

const input = readJson(resolvedPath);

// Accept any of the three shapes described above.
let deps;
if (Array.isArray(input)) {
  deps = input;
} else if (Array.isArray(input?.resolved?.templateDependencyMetadata)) {
  deps = input.resolved.templateDependencyMetadata;
} else if (Array.isArray(input?.templateDependencyMetadata)) {
  deps = input.templateDependencyMetadata;
} else {
  // No recognized deploy-ready shape: not a bare templateDependencyMetadata
  // array, not a resolve-template.mjs DEPLOY output (its `.resolved` is null on a
  // STOP_AMBIGUOUS / STOP_NOT_FOUND / SELF_HEAL), and not a single template
  // object. Fail loud rather than emit a valid-but-empty {"flowTemplates":[]}
  // that is indistinguishable from a dependency-free template — piping a stop /
  // null resolution into the builder must produce an error signal, never a body.
  process.stderr.write(
    'build-deploy-payload: input is not a deploy-ready template (no ' +
      'templateDependencyMetadata found; a STOP / null resolution has ' +
      'resolved:null and cannot build a deploy body). Refusing to emit an empty body.\n',
  );
  process.exit(2);
}

// The ONLY constructed field is templateVariables (defaults to {}); every enum
// is echoed verbatim, with a defined fallback key when the primary is absent.
const flowTemplates = deps.map((dep) => {
  const el = {
    templateType: dep.templateType, // verbatim: "INTAKE" | "FULFILLMENT"
    templateApiName: dep.templateApiName ?? dep.dependencyApiName, // first non-empty
    templateDependencyType: dep.templateDependencyType ?? dep.dependencyType, // verbatim: "FLOW"
    dependencyDeploymentMedium: dep.dependencyDeploymentMedium, // verbatim: "APP_FRAMEWORK"
    templateVariables:
      dep.templateVariables && typeof dep.templateVariables === 'object' ? dep.templateVariables : {},
  };
  return el;
});

const body = { flowTemplates };

// Merge user-supplied optional fields — but only keys that are actually present
// (never send empty strings/nulls; omit the key entirely).
if (optionalPath) {
  const optional = readJson(optionalPath);
  for (const key of ['description', 'isActive', 'deploymentMode', 'catalog', 'category', 'serviceProcessName']) {
    if (optional[key] !== undefined && optional[key] !== null && optional[key] !== '') {
      body[key] = optional[key];
    }
  }
}

process.stdout.write(JSON.stringify(body) + '\n');
