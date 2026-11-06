#!/usr/bin/env node
// Retrieve the non-secret OAuth consumer key for a deployed ECA.
//
// Usage: node retrieve_eca_consumer_key.mjs <target-org-alias> <eca-developer-name> [oauth-consumer-id] [--json]
//
// Exit 0 with JSON `status`:
//   not_found          - the query succeeded and no ExternalClientApplication matched that DeveloperName.
//   selection_required - more than one OAuth consumer; the caller must choose an id.
// With --json and a single consumer, prints the key object (no `status`); without --json, prints the bare key.
// Exit 1: lookup, API, or response validation failed. Do not infer that the ECA is absent.
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { isValidDeveloperName } from "./developer_name.mjs";

function fail(msg, code = 1) {
  process.stderr.write(msg + "\n");
  process.exit(code);
}

const jsonOutput = process.argv.slice(2).includes("--json");
const args = process.argv.slice(2).filter((arg) => arg !== "--json");
if (args.length < 2 || args.length > 3) {
  fail("Usage: retrieve_eca_consumer_key.mjs <target-org-alias> <eca-developer-name> [oauth-consumer-id] [--json]");
}
const [targetOrg, ecaDeveloperName, oauthConsumerId = ""] = args;
if (!targetOrg || targetOrg.startsWith("-")) fail("ERROR: target org alias is invalid.");

let apiVersion;
try {
  apiVersion = JSON.parse(fs.readFileSync("sfdx-project.json", "utf-8")).sourceApiVersion;
  if (!/^\d{2,3}\.0$/.test(apiVersion)) throw new Error("Invalid sourceApiVersion");
} catch {
  fail("ERROR: run from an SFDX project root with a valid sourceApiVersion.");
}
if (!isValidDeveloperName(ecaDeveloperName)) {
  fail("ERROR: ECA developer name is invalid.");
}
if (oauthConsumerId && !/^[A-Za-z0-9]+$/.test(oauthConsumerId)) {
  fail("ERROR: OAuth consumer ID is invalid.");
}

function requestJson(url, description) {
  let body;
  try {
    body = execFileSync(
      "sf",
      ["api", "request", "rest", url, "--target-org", targetOrg, "--method", "GET"],
      { encoding: "utf-8" },
    );
  } catch {
    process.stderr.write(`ERROR: ${description} request failed.\n`);
    return null;
  }
  try {
    return JSON.parse(body);
  } catch {
    process.stderr.write(`ERROR: ${description} returned invalid JSON.\n`);
    return null;
  }
}

const ecaSoql = `SELECT Id FROM ExternalClientApplication WHERE DeveloperName = '${ecaDeveloperName}'`;
let ecaQueryRaw;
try {
  ecaQueryRaw = execFileSync(
    "sf",
    ["data", "query", "--query", ecaSoql, "--target-org", targetOrg, "--api-version", apiVersion, "--json"],
    { encoding: "utf-8" },
  );
} catch {
  fail("ERROR: ECA query failed.");
}
let ecaQuery;
try {
  ecaQuery = JSON.parse(ecaQueryRaw);
} catch {
  ecaQuery = null;
}
const ecaOk =
  ecaQuery &&
  ecaQuery.status === 0 &&
  typeof ecaQuery.result?.totalSize === "number" &&
  Array.isArray(ecaQuery.result?.records) &&
  ecaQuery.result.totalSize === ecaQuery.result.records.length &&
  ecaQuery.result.records.every((r) => typeof r.Id === "string");
if (!ecaOk) fail("ERROR: ECA query returned an unrecognized response.");

const matchCount = ecaQuery.result.totalSize;
// A successful query that proved absence is an answer (exit 0); anything inconclusive fails.
if (matchCount === 0) {
  console.log(JSON.stringify({
    status: "not_found",
    message: `no deployed ECA matched developer name ${ecaDeveloperName}`,
    ecaDeveloperName,
  }));
  process.exit(0);
}
if (matchCount !== 1) fail(`ERROR: multiple deployed ECAs matched developer name ${ecaDeveloperName}.`);

const ecaIdentifier = ecaQuery.result.records[0].Id;
if (!/^[A-Za-z0-9]+$/.test(ecaIdentifier)) fail("ERROR: ECA lookup returned an invalid identifier.");

const credentialsUrl = `/services/data/v${apiVersion}/apps/oauth/credentials/${ecaIdentifier}?part=key`;
const credentials = requestJson(credentialsUrl, "OAuth consumer lookup");
if (!credentials) process.exit(1);
const credsOk =
  Array.isArray(credentials.consumers) &&
  credentials.consumers.every(
    (c) => typeof c.id === "string" && typeof c.name === "string" && typeof c.key === "string",
  );
if (!credsOk) fail("ERROR: OAuth consumer lookup returned an unrecognized response.");

const consumerCount = credentials.consumers.length;
if (consumerCount === 0) fail("ERROR: deployed ECA has no OAuth consumers.");

let selected;
if (oauthConsumerId) {
  selected = credentials.consumers.filter((c) => c.id === oauthConsumerId);
  if (selected.length !== 1) {
    fail(`ERROR: OAuth consumer ID ${oauthConsumerId} did not match exactly one consumer.`);
  }
} else if (consumerCount === 1) {
  selected = [credentials.consumers[0]];
} else {
  console.log(
    JSON.stringify({
      status: "selection_required",
      apiVersion,
      eca: { developerName: ecaDeveloperName, identifier: ecaIdentifier },
      consumerCandidates: credentials.consumers.map((c) => ({ id: c.id, name: c.name })),
    }),
  );
  process.exit(0);
}

if (!selected[0].key.trim()) fail("ERROR: OAuth consumer key is empty.");
console.log(jsonOutput ? JSON.stringify({
  apiVersion,
  ecaDeveloperName,
  ecaId: ecaIdentifier,
  oauthConsumerId: selected[0].id,
  clientId: selected[0].key,
}) : selected[0].key);
