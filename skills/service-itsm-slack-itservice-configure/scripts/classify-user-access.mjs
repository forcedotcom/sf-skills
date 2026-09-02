#!/usr/bin/env node
// Deterministic helpers for Step 4 (Manage User Access) of the Slack Employee
// Service setup, so the model never eyeballs a response body.
//
// Two sub-commands:
//
//   flag-users <users-query.json>
//     Reads the User SOQL response (the {records:[...]} envelope from
//     /services/data/vXX.0/query) and tags each row as "employee" or "system"
//     using a fixed heuristic — WITHOUT dropping any row. System/integration
//     accounts (Automated Process, Bot User, Insights Integration, *.ext,
//     ESW_* / *Site Guest User, DigitalAgent.*, *@00d* platform users) are
//     flagged so the user isn't asked to guess, but they are still listed.
//     Prints {users:[{id,name,username,email,kind}], employeeCount, systemCount}.
//
//   classify-assignment <assignment-response.json>
//     Reads the PermissionSetAssignment POST result and classifies it as
//     "success" (201 / has an id), "wrong-license" (a 400
//     FIELD_INTEGRITY_EXCEPTION about the Slack permission-set license not
//     being supported by the user's license — a HARD stop, do not retry), or
//     "other-error". Prints {status, retryable, message}.
//
// Both read their input from a file path (pass the captured response JSON).
// Exits 2 on missing/bad args, 3 on unreadable/unparseable input.

import { readFileSync } from 'node:fs';

const [cmd, inPath] = process.argv.slice(2);

// headless-360 `dispatch`/`dispatch_readonly` may hand back either the raw
// Salesforce payload or an envelope like { status_code, body } / { statusCode,
// body } / { data }. Unwrap to the underlying Salesforce payload so both the
// user-query and the assignment-response classifiers see the shape they expect
// regardless of how the response was captured. (Idempotent: a raw payload with
// no envelope key is returned unchanged.)
function unwrapEnvelope(data) {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    const hasEnvelopeMarker =
      'status_code' in data || 'statusCode' in data || 'httpStatusCode' in data;
    if (hasEnvelopeMarker && data.body !== undefined) return data.body;
    // A lone { data: ... } wrapper (no status marker) is also an envelope.
    if (
      data.body === undefined &&
      data.data !== undefined &&
      !('records' in data) &&
      !('id' in data) &&
      !('Id' in data)
    ) {
      return data.data;
    }
  }
  return data;
}

function die(code, msg) {
  process.stderr.write(`${msg}\n`);
  process.exit(code);
}

function loadJson(path) {
  if (!path) die(2, 'usage: node classify-user-access.mjs <flag-users|classify-assignment> <response.json>');
  let raw;
  try {
    raw = readFileSync(path, 'utf8');
  } catch {
    die(3, `error: could not read ${path}`);
  }
  try {
    return JSON.parse(raw);
  } catch {
    die(3, `error: could not parse JSON in ${path}`);
  }
}

// A row is a system/integration account (flag, don't drop) if its Name or
// Username matches any of these fixed patterns. Case-insensitive.
const SYSTEM_NAME_PATTERNS = [
  /^automated process$/i,
  /^bot user$/i,
  /insights? integration/i,
  /integration user/i,
  /site guest user/i,
  /^chatter expert$/i,
  /^security user$/i,
  /^analytics cloud/i,
  /platform integration user/i,
];
const SYSTEM_USERNAME_PATTERNS = [
  /\.ext@/i, // *.ext users
  /^esw_/i, // ESW_* embedded-service users
  /^digitalagent\./i, // DigitalAgent.* agent users
  /@00d/i, // *@00d... platform/site users
  /autoproc@/i,
  /insightssecurity@/i,
];

function classifyUserKind(name, username) {
  const n = String(name ?? '');
  const u = String(username ?? '');
  const isSystem =
    SYSTEM_NAME_PATTERNS.some((re) => re.test(n)) ||
    SYSTEM_USERNAME_PATTERNS.some((re) => re.test(u));
  return isSystem ? 'system' : 'employee';
}

function flagUsers(data) {
  const records = Array.isArray(data?.records) ? data.records : Array.isArray(data) ? data : [];
  const users = records.map((r) => {
    const kind = classifyUserKind(r?.Name, r?.Username);
    return {
      id: r?.Id ?? null,
      name: r?.Name ?? null,
      username: r?.Username ?? null,
      email: r?.Email ?? null,
      kind,
    };
  });
  const employeeCount = users.filter((u) => u.kind === 'employee').length;
  const systemCount = users.length - employeeCount;
  return { users, employeeCount, systemCount };
}

// Salesforce error responses come back as an array of {errorCode, message} or
// a single object; normalize and classify.
function classifyAssignment(data) {
  // Success shapes: {id, success:true} (sObject POST) or {Id: "0Pa..."}.
  const id = data?.id ?? data?.Id ?? null;
  if (id && data?.success !== false) {
    return { status: 'success', retryable: false, message: 'Permission set assigned.' };
  }

  const errors = Array.isArray(data) ? data : Array.isArray(data?.errors) ? data.errors : [data];
  const first = errors.find((e) => e && (e.errorCode || e.message)) ?? {};
  const errorCode = String(first.errorCode ?? '');
  const message = String(first.message ?? '');

  const looksLikeLicenseMismatch =
    /FIELD_INTEGRITY_EXCEPTION/i.test(errorCode) &&
    /(permission set license|user license)/i.test(message) &&
    /(support|assigned)/i.test(message);

  if (looksLikeLicenseMismatch) {
    return {
      status: 'wrong-license',
      retryable: false,
      message:
        "This user's license can't hold this permission set. Pick a user on a compatible " +
        'license (a Standard User works) rather than retrying.',
    };
  }

  return {
    status: 'other-error',
    retryable: false,
    message: message || errorCode || 'Assignment failed for an unknown reason.',
  };
}

const data = unwrapEnvelope(loadJson(inPath));

if (cmd === 'flag-users') {
  process.stdout.write(JSON.stringify(flagUsers(data), null, 2) + '\n');
} else if (cmd === 'classify-assignment') {
  process.stdout.write(JSON.stringify(classifyAssignment(data), null, 2) + '\n');
} else {
  die(2, 'usage: node classify-user-access.mjs <flag-users|classify-assignment> <response.json>');
}
