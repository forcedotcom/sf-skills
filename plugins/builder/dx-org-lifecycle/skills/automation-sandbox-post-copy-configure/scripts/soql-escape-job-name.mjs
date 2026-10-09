#!/usr/bin/env node
// Deterministic JobName → SOQL-safe literal helper for Step F-1 / F-4
// pre-flight and verify SOQL. A human-readable JobName may legitimately
// contain characters (e.g. an apostrophe in "Owner's nightly job") that
// break out of a raw single-quoted SOQL literal. This helper rejects
// characters that would also break the F-2 Apex snippet (kept in
// lockstep with build-scheduled-apex.mjs) and escapes single quotes for
// SOQL, so both the pre-flight query and the anonymous Apex snippet
// operate on the same validated JobName.
//
// Exits 0 with the escaped literal on stdout, or non-zero with a
// single-line reason on stderr.

const [, , jobName] = process.argv;

if (jobName === undefined) {
  process.stderr.write('usage: node soql-escape-job-name.mjs <JobName>\n');
  process.exit(2);
}

if (/[\r\n\\]/.test(jobName)) {
  process.stderr.write(
    `ERROR: JobName contains a newline or backslash: ${JSON.stringify(jobName)}\n`
  );
  process.exit(2);
}

process.stdout.write(jobName.replaceAll("'", "\\'"));
