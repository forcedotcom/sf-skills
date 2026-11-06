#!/usr/bin/env node
// List runtime-available Apex and Flow invocable actions without retrieving
// metadata or writing to the current SFDX project.
//
// Usage: node retrieve_existing_tools.mjs <target-org-alias>
import fs from "node:fs";
import { execFileSync } from "node:child_process";

function fail(msg, code = 1) {
  process.stderr.write(msg + "\n");
  process.exit(code);
}

const args = process.argv.slice(2);
if (args.length !== 1) {
  fail("Usage: retrieve_existing_tools.mjs <target-org-alias>");
}
const [targetOrg] = args;
const apiVersion = JSON.parse(fs.readFileSync("sfdx-project.json", "utf-8")).sourceApiVersion;

function requestActions(backing) {
  let body;
  try {
    body = execFileSync(
      "sf",
      [
        "api",
        "request",
        "rest",
        `/services/data/v${apiVersion}/actions/custom/${backing}`,
        "--target-org",
        targetOrg,
        "--method",
        "GET",
      ],
      { encoding: "utf-8" },
    );
  } catch {
    process.stderr.write(`ERROR: ${backing} invocable-action discovery failed.\n`);
    return null;
  }
  let parsed;
  try {
    parsed = JSON.parse(body);
  } catch {
    parsed = null;
  }
  const ok =
    parsed &&
    Array.isArray(parsed.actions) &&
    parsed.actions.every((a) => typeof a.name === "string" && typeof a.url === "string");
  if (!ok) {
    process.stderr.write(`ERROR: ${backing} discovery returned an unrecognized response.\n`);
    process.stderr.write(body + "\n");
    return null;
  }
  return parsed;
}

const apex = requestActions("apex");
if (!apex) process.exit(1);
const flow = requestActions("flow");
if (!flow) process.exit(1);

console.log(
  JSON.stringify({
    apiVersion,
    candidateCounts: { apex: apex.actions.length, flow: flow.actions.length },
    apex: apex.actions,
    flow: flow.actions,
  }),
);
