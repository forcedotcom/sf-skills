#!/usr/bin/env node
// Deterministic Step F-2 helper: render assets/scheduled_apex_template.apex
// with a config entry's JobName / CronExpression / ApexClassName. Emits
// the substituted snippet to stdout; non-zero exit on any validation
// failure with a single-line human-readable reason on stderr.
//
// Kept out of SKILL.md prose per authoring standard A9 — string escaping
// and cron/identifier validation are deterministic and belong in scripts/.

import { readFileSync } from 'node:fs';

const [, , jobName, cronExpression, apexClassName, templatePath] = process.argv;

if (!jobName || !cronExpression || !apexClassName || !templatePath) {
  process.stderr.write(
    'usage: node build-scheduled-apex.mjs <JobName> <CronExpression> <ApexClassName> <template-path>\n'
  );
  process.exit(2);
}

// Reject characters that break out of the Apex single-quoted string
// literal we substitute into. Newlines are a compile error; backslash
// is not a general escape in Apex string literals and lets a crafted
// value inject arbitrary Apex.
const forbidden = /[\r\n\\]/;
for (const [name, value] of [
  ['JobName', jobName],
  ['CronExpression', cronExpression],
  ['ApexClassName', apexClassName],
]) {
  if (forbidden.test(value)) {
    process.stderr.write(
      `ERROR: ${name} contains a newline or backslash: ${JSON.stringify(value)}\n`
    );
    process.exit(2);
  }
}

const cronFields = cronExpression.trim().split(/\s+/).length;
if (cronFields !== 6 && cronFields !== 7) {
  process.stderr.write(
    `ERROR: CronExpression must be 6 or 7 whitespace-separated fields; got ${cronFields}: ${JSON.stringify(cronExpression)}\n`
  );
  process.exit(2);
}

if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(apexClassName)) {
  process.stderr.write(
    `ERROR: ApexClassName must be a bare Apex identifier (letters, digits, underscore, not starting with a digit): ${JSON.stringify(apexClassName)}\n`
  );
  process.exit(2);
}

const escapeApexSingleQuoted = (s) => s.replaceAll("'", "\\'");

const template = readFileSync(templatePath, 'utf8');
const rendered = template
  .replaceAll('{{JOB_NAME}}', escapeApexSingleQuoted(jobName))
  .replaceAll('{{CRON_EXPRESSION}}', escapeApexSingleQuoted(cronExpression))
  .replaceAll('{{APEX_CLASS_NAME}}', apexClassName);

process.stdout.write(rendered);
