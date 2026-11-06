#!/usr/bin/env node
// Render ECA metadata, or compare existing files with the same templates.
//
// Usage: node render_eca.mjs <METADATA_DIR> <ECA_DEV_NAME> <ECA_LABEL> <ECA_DESC> <CONTACT_EMAIL> <CALLBACK_URLS>
// Optional: --permitted-users-policy <AdminApprovedPreAuthorized|AllSelfAuthorized>.
// Add --check for read-only comparison; metadata directory and ECA name alone
// check fixed fields while leaving unconfirmed input fields unverified.
//
// Reads the flat __ECA_NAME__*.xml templates from assets/, substitutes
// placeholders, renames each to <ECA_DEV_NAME>, and writes it under METADATA_DIR.
// METADATA_DIR is <default-package>/main/default, passed by the skill. Run from the project root.
//
// CALLBACK_URLS is a required space- or comma-separated list of absolute
// client redirect URIs. Empty values and wildcards are rejected.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { callbackRejection } from "./utils/callback_url.mjs";
import { isValidDeveloperName } from "./utils/developer_name.mjs";
import { checkEcaPlan } from "./utils/eca_check.mjs";
import { requireProjectDestination } from "./utils/metadata_path.mjs";

function fail(msg) {
  process.stderr.write(msg + "\n");
  process.exit(1);
}

const args = [];
let checkOnly = false;
let permittedUsersPolicy;
const rawArgs = process.argv.slice(2);
for (let i = 0; i < rawArgs.length; i++) {
  const arg = rawArgs[i];
  if (arg === "--check" && !checkOnly) {
    checkOnly = true;
  } else if (arg === "--permitted-users-policy" && permittedUsersPolicy === undefined) {
    permittedUsersPolicy = rawArgs[++i];
    if (!["AdminApprovedPreAuthorized", "AllSelfAuthorized"].includes(permittedUsersPolicy)) {
      fail("--permitted-users-policy must be AdminApprovedPreAuthorized or AllSelfAuthorized.");
    }
  } else if (arg.startsWith("--")) {
    fail(`Unknown or duplicate option: ${arg}`);
  } else {
    args.push(arg);
  }
}
permittedUsersPolicy ??= "AdminApprovedPreAuthorized";
if (args.length !== 6 && !(checkOnly && args.length === 2)) {
  fail("Usage: render_eca.mjs <METADATA_DIR> <ECA_DEV_NAME> [<ECA_LABEL> <ECA_DESC> <CONTACT_EMAIL> <CALLBACK_URLS>] --check; omit --check and supply all inputs to create files.");
}
const [metadataDirArg, ecaName, ecaLabel, ecaDesc, contactEmail, callbackUrls] = args;

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const assetDir = path.join(scriptDir, "..", "assets");
const projectRoot = path.resolve(process.cwd());
const defaultDir = path.resolve(projectRoot, metadataDirArg);
if (defaultDir !== projectRoot && !defaultDir.startsWith(projectRoot + path.sep)) {
  fail(`ABORT: metadata directory '${metadataDirArg}' escapes the project root`);
}

// DeveloperName is used in filenames, so validate it before constructing paths.
if (!isValidDeveloperName(ecaName)) {
  fail(
    `Invalid DeveloperName '${ecaName}': letters, digits, single underscores, optional namespace__ prefix, start with a letter, <= 80 chars.`,
  );
}

// Map each template suffix to its metadata source directory. Order matters:
// more specific suffixes must be matched before more general ones.
function folderFor(base) {
  if (base.endsWith(".ecaGlblOauth-meta.xml")) return "extlClntAppGlobalOauthSets";
  if (base.endsWith(".ecaOauthPlcy-meta.xml")) return "extlClntAppOauthPolicies";
  if (base.endsWith(".ecaOauth-meta.xml")) return "extlClntAppOauthSettings";
  if (base.endsWith(".ecaPlcy-meta.xml")) return "extlClntAppPolicies";
  if (base.endsWith(".eca-meta.xml")) return "externalClientApps";
  return "";
}

const templates = fs.existsSync(assetDir)
  ? fs.readdirSync(assetDir).filter((f) => f.startsWith("__ECA_NAME__") && f.endsWith(".xml"))
  : [];
if (templates.length === 0) {
  fail(`No __ECA_NAME__*.xml templates found in ${assetDir}`);
}

function escapeXml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const replacements = { __ECA_NAME__: ecaName };
if (args.length === 6) {
  const callbacks = callbackUrls.trim().split(/[,\s]+/).filter(Boolean);
  if (callbacks.length === 0) fail("ABORT: at least one callback URL is required. There is no safe default redirect.");
  for (const callback of callbacks) {
    const rejection = callbackRejection(callback);
    if (rejection) fail(`ABORT: ${rejection}`);
  }
  Object.assign(replacements, {
    __ECA_LABEL__: escapeXml(ecaLabel),
    __ECA_DESC__: escapeXml(ecaDesc),
    __ECA_CONTACT_EMAIL__: escapeXml(contactEmail),
    __ECA_CALLBACK_URLS__: callbacks.map(escapeXml).join("\n"),
  });
}

// Check every destination before writing any of them so a collision cannot
// leave a partially rendered ECA in the project.
const plan = [];
for (const base of templates) {
  const folder = folderFor(base);
  if (!folder) fail(`Unknown metadata suffix for ${base}.`);
  // Strip the __ECA_NAME__ prefix to keep any compound suffix (e.g.
  // _defaultPolicy.ecaPlcy-meta.xml), then re-prefix with the real name.
  const suffix = base.slice("__ECA_NAME__".length);
  const destDir = path.join(defaultDir, folder);
  const dest = path.join(destDir, `${ecaName}${suffix}`);
  if (!checkOnly) {
    try {
      requireProjectDestination(projectRoot, dest);
    } catch {
      fail("ABORT: metadata destination is unreadable or resolves outside the project root");
    }
  }
  if (!checkOnly && fs.lstatSync(dest, { throwIfNoEntry: false })) fail(`Refuse to overwrite existing file: ${dest}`);
  const src = path.join(assetDir, base);
  const template = fs.readFileSync(src, "utf8").replace(
    "<permittedUsersPolicyType>AdminApprovedPreAuthorized</permittedUsersPolicyType>",
    `<permittedUsersPolicyType>${permittedUsersPolicy}</permittedUsersPolicyType>`,
  );
  let expected = template;
  for (const [key, value] of Object.entries(replacements)) expected = expected.split(key).join(value);
  plan.push({ src, destDir, dest, template, expected });
}

if (checkOnly) {
  const report = checkEcaPlan(plan);
  console.log(JSON.stringify(report, null, 2));
} else {
  for (const { destDir, dest, expected } of plan) {
    fs.mkdirSync(destDir, { recursive: true });
    fs.writeFileSync(dest, expected, "utf-8");
  }
  console.log(`Rendered ECA metadata in ${defaultDir}`);
}
