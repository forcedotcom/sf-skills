#!/usr/bin/env node
// Resolve + set the Experience Cloud site logout URL (deploy step 3b).
//
// Deterministic helper for the "site logout URL" step: it resolves the shipped
// (site-relative or absolute) logoutUrl config value to the ABSOLUTE URL the
// platform requires, writes it idempotently into the site's network metadata,
// and (optionally) deploys just that file. The SKILL.md step invokes this
// instead of re-deriving the algorithm in prose. Faithful port of the reference
// org-setup.mjs helpers (org-setup-url.mjs + org-setup-xml.mjs).
//
// Why absolute + post-deploy: the platform rejects a relative logout URL at
// deploy time ("The logout page URL must be an absolute URL."), and a shipped
// site-relative path is resolved against the site's Experience Cloud origin,
// which only exists once the site is deployed.
//
// Usage:
//   node scripts/set-logout-url.mjs \
//     --logout-url "/myapp/" \
//     --network-file <sourceRoot>/networks/<site>.network-meta.xml \
//     --target-org <org> \
//     [--site <siteName>] [--deploy]
//
// Exit codes:
//   0  applied (changed), already-correct (unchanged), or deployed
//   3  best-effort SKIP (file missing / origin unresolvable / XML-special char /
//      deploy failure) — NOT a setup failure; the caller logs loudly and continues
//   1  usage / argument error
//
// A skip (exit 3) means: tell the user to set the logout URL manually in the
// site's Administration settings (Setup -> Digital Experiences -> the site ->
// Administration -> Login & Registration -> Logout URL).

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

// Connect "communities" REST resource. Its API version is resolved from the org
// at runtime (see resolveApiVersion) so it never goes stale as versions
// increment; this pinned floor — the version used by the reference org-setup.mjs
// port — is the fallback used only when that lookup fails. This step reads just
// `siteUrl`/`name`, whose shape is stable across versions, so the exact version
// is not load-bearing.
const FALLBACK_API_VERSION = 'v62.0';
const XML_SPECIAL_CHARS = /[&<>"']/;

// ---- argument parsing -------------------------------------------------------

function parseArgs(argv) {
  const args = { deploy: false };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    switch (a) {
      case '--logout-url': args.logoutUrl = argv[++i]; break;
      case '--network-file': args.networkFile = argv[++i]; break;
      case '--target-org': args.targetOrg = argv[++i]; break;
      case '--site': args.site = argv[++i]; break;
      case '--deploy': args.deploy = true; break;
      default:
        fail(1, `unknown argument: ${a}`);
    }
  }
  if (!args.logoutUrl) fail(1, 'missing --logout-url');
  if (!args.networkFile) fail(1, 'missing --network-file');
  if (!args.targetOrg) fail(1, 'missing --target-org');
  return args;
}

function fail(code, message) {
  console.error(`set-logout-url: ${message}`);
  process.exit(code);
}

function skip(message) {
  console.error(
    `set-logout-url: SKIP — ${message}. Set the logout URL manually in the site's ` +
      `Administration settings (Login & Registration -> Logout URL).`,
  );
  process.exit(3);
}

// ---- pure URL helpers (port of org-setup-url.mjs) ---------------------------

/** True when `value` is an absolute http(s) URL — already deployable as-is. */
function isAbsoluteLogoutUrl(value) {
  return /^https?:\/\//i.test(String(value).trim());
}

/** Leading path segment of a URL or path: "/app/" -> "app", "/" -> "". */
function firstPathSegment(pathOrUrl) {
  let pathname;
  try {
    pathname = new URL(pathOrUrl).pathname; // absolute URL
  } catch {
    pathname = String(pathOrUrl).split(/[?#]/)[0]; // relative path
  }
  return pathname.replace(/^\/+/, '').split('/')[0];
}

/**
 * Choose the community whose siteUrl anchors a relative logout path — match on
 * the siteUrl PATH first, then on `name` == siteName. Never guesses an arbitrary
 * community (resolving against the wrong origin yields a valid-but-wrong URL).
 */
function pickCommunityBaseUrl(communities, configLogoutUrl, siteName) {
  const list = Array.isArray(communities) ? communities.filter((c) => c && c.siteUrl) : [];
  const seg = firstPathSegment(configLogoutUrl);
  if (seg) {
    const byPath = list.find((c) => firstPathSegment(c.siteUrl) === seg);
    if (byPath) return byPath.siteUrl;
  }
  if (siteName) {
    const byName = list.find((c) => c.name === siteName);
    if (byName) return byName.siteUrl;
  }
  return null;
}

/** Resolve a config value to an absolute URL (relative -> against baseUrl origin). */
function resolveLogoutUrl(configLogoutUrl, baseUrl) {
  const value = String(configLogoutUrl).trim();
  if (isAbsoluteLogoutUrl(value)) return value;
  if (!baseUrl) {
    throw new Error(
      `logout URL "${configLogoutUrl}" is site-relative but no Experience Cloud community ` +
        `site URL was found to resolve it into an absolute URL`,
    );
  }
  let resolved;
  try {
    resolved = new URL(value, baseUrl).href;
  } catch (e) {
    throw new Error(`could not resolve "${configLogoutUrl}" against "${baseUrl}": ${e.message}`);
  }
  if (!isAbsoluteLogoutUrl(resolved)) {
    throw new Error(`resolved logout URL "${resolved}" is not an absolute http(s) URL`);
  }
  return resolved;
}

// ---- XML helpers (port of org-setup-xml.mjs setLogoutUrl) -------------------

/** Direct child element names of <Network> (depth-aware, no XML deps). */
function networkChildNames(xml) {
  const open = xml.match(/<Network\b[^>]*>/);
  const close = xml.lastIndexOf('</Network>');
  if (!open || close === -1) return [];
  const inner = xml.slice(open.index + open[0].length, close);
  const tag = /<(\/?)([A-Za-z_][\w.-]*)\b[^>]*?(\/?)>/g;
  const names = new Set();
  let depth = 0;
  let m;
  while ((m = tag.exec(inner)) !== null) {
    const [, closing, name, selfClose] = m;
    if (closing) {
      depth -= 1;
    } else if (selfClose) {
      if (depth === 0) names.add(name);
    } else {
      if (depth === 0) names.add(name);
      depth += 1;
    }
  }
  return [...names];
}

function firstChildIndent(xml) {
  const m = xml.match(/\n([ \t]+)<[A-Za-z_]/);
  return m ? m[1] : '    ';
}

/**
 * Returns { xml, changed }. Idempotent (unchanged when already equal); replaces
 * an existing value in place; else inserts <logoutUrl> in the canonical
 * alphabetical position among Network's top-level children. Throws on an
 * XML-special char in the URL (reject, don't escape).
 */
function setLogoutUrl(xml, url) {
  if (XML_SPECIAL_CHARS.test(String(url))) {
    throw new Error(`logoutUrl "${url}" contains an XML-special character (& < > " ')`);
  }
  const node = `<logoutUrl>${url}</logoutUrl>`;
  const existing = xml.match(/<logoutUrl>([^<]*)<\/logoutUrl>/);
  if (existing) {
    if (existing[1] === url) return { xml, changed: false };
    return { xml: xml.replace(/<logoutUrl>[^<]*<\/logoutUrl>/, node), changed: true };
  }
  // Absent — insert before the first top-level sibling that sorts after "logoutUrl".
  const successor = networkChildNames(xml)
    .filter((name) => name > 'logoutUrl')
    .sort()[0];
  if (successor) {
    const beforeSuccessor = new RegExp(`(\\n[ \\t]*)(<${successor}\\b)`);
    if (beforeSuccessor.test(xml)) {
      return { xml: xml.replace(beforeSuccessor, `$1${node}$1$2`), changed: true };
    }
  }
  const indent = firstChildIndent(xml);
  const beforeClose = /(\n)([ \t]*<\/Network>)/;
  if (beforeClose.test(xml)) {
    return { xml: xml.replace(beforeClose, `\n${indent}${node}$1$2`), changed: true };
  }
  return { xml: xml.replace(/(<Network\b[^>]*>)/, `$1\n${indent}${node}`), changed: true };
}

// ---- org I/O ----------------------------------------------------------------

/**
 * Resolve the org's highest supported REST API version (e.g. "v66.0") via the
 * version-less `/services/data/` endpoint. Falls back to FALLBACK_API_VERSION
 * if the lookup fails or returns nothing usable, so resolution is never worse
 * than a fixed pin.
 */
function resolveApiVersion(targetOrg) {
  try {
    const out = execFileSync(
      'sf',
      ['api', 'request', 'rest', '/services/data/', '--target-org', targetOrg],
      { encoding: 'utf8', timeout: 120000 },
    );
    const versions = JSON.parse(out);
    const max = Array.isArray(versions)
      ? versions
          .map((v) => parseFloat(v && v.version))
          .filter((n) => !Number.isNaN(n))
          .sort((a, b) => a - b)
          .pop()
      : undefined;
    if (max) return `v${max.toFixed(1)}`;
  } catch {
    // Unreachable org, unexpected shape, etc. — fall through to the pinned floor.
  }
  return FALLBACK_API_VERSION;
}

function fetchCommunities(targetOrg) {
  const apiVersion = resolveApiVersion(targetOrg);
  const out = execFileSync(
    'sf',
    ['api', 'request', 'rest', `/services/data/${apiVersion}/connect/communities`, '--target-org', targetOrg],
    { encoding: 'utf8', timeout: 120000 },
  );
  const parsed = JSON.parse(out);
  return Array.isArray(parsed.communities) ? parsed.communities : [];
}

function deployNetworkFile(networkFile, targetOrg) {
  execFileSync(
    'sf',
    ['project', 'deploy', 'start', '--source-dir', networkFile, '--target-org', targetOrg],
    { stdio: 'inherit', timeout: 120000 },
  );
}

// ---- main -------------------------------------------------------------------

function main() {
  const args = parseArgs(process.argv.slice(2));

  if (!existsSync(args.networkFile)) {
    skip(`network metadata not found: ${args.networkFile}`);
  }

  // 1. Resolve to an absolute URL.
  let absoluteUrl;
  try {
    let baseUrl = null;
    if (!isAbsoluteLogoutUrl(args.logoutUrl)) {
      baseUrl = pickCommunityBaseUrl(fetchCommunities(args.targetOrg), args.logoutUrl, args.site);
    }
    absoluteUrl = resolveLogoutUrl(args.logoutUrl, baseUrl);
  } catch (e) {
    skip(`cannot resolve an absolute logout URL — ${e.message}`);
  }

  // 2. Write it into the network metadata (idempotent).
  let result;
  try {
    result = setLogoutUrl(readFileSync(args.networkFile, 'utf8'), absoluteUrl);
  } catch (e) {
    skip(`cannot set <logoutUrl> in ${args.networkFile} — ${e.message}`);
  }

  if (!result.changed) {
    console.log(`logout URL already set to "${absoluteUrl}"; no change (skipping deploy).`);
    process.exit(0);
  }
  writeFileSync(args.networkFile, result.xml);
  console.log(`set <logoutUrl>${absoluteUrl}</logoutUrl> in ${args.networkFile}`);

  // 3. Deploy only that file (best-effort).
  if (args.deploy) {
    try {
      deployNetworkFile(args.networkFile, args.targetOrg);
      console.log(`deployed <logoutUrl> for "${args.site || args.networkFile}".`);
    } catch (e) {
      skip(
        `failed to deploy the network file (${e.message}). If the org's Network ` +
          `emailSenderAddress differs from the shipped value it can block this deploy`,
      );
    }
  }
  process.exit(0);
}

main();
