#!/usr/bin/env node
// Deterministic queue-advancement gate (authoring standard A9). Each child
// skill already emits its own machine-readable verdict — Studio's `overall`
// from classify-final-report.mjs, Fulfiller/Employee's Phase 8 aggregate — so
// this script only maps those fixed value sets to an advance/stop decision.
// It must not be re-derived in prose; the coordinator runs this and reads the
// exit code.
//
// Usage:
//   node verify-child-verdict.mjs <studio|fulfiller|employee> <verdict>
//
// Exit 0  -> child succeeded, safe to advance the queue.
// Exit 1  -> child failed or only partially succeeded, stop the queue.
// Exit 2  -> usage error (bad args).

const SUCCESS_VALUES = {
  studio: new Set(['SUCCESS']),
  fulfiller: new Set(['CREATED', 'ALREADY-CREATED', 'ACTIVATED']),
  employee: new Set(['CREATED', 'ALREADY-CREATED', 'ACTIVATED']),
};

const [child, verdict] = process.argv.slice(2);

if (!child || !verdict || !SUCCESS_VALUES[child]) {
  process.stderr.write('usage: node verify-child-verdict.mjs <studio|fulfiller|employee> <verdict>\n');
  process.exit(2);
}

if (SUCCESS_VALUES[child].has(verdict)) {
  process.stdout.write(`ADVANCE: ${child} verdict "${verdict}" is a success value.\n`);
  process.exit(0);
}

process.stdout.write(`STOP: ${child} verdict "${verdict}" is not a success value — do not advance the queue.\n`);
process.exit(1);
