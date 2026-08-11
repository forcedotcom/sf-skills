/**
 * Pure, importable XML helpers for org-setup.mjs network-metadata mutation
 * (W-23043734 — Infrastructure Hygiene).
 *
 * These functions replace the script's former blind-regex editing of
 * `*.network-meta.xml`. The contract is:
 *
 *   1. Parse the XML with `fast-xml-parser` ONLY to assert the expected nodes
 *      exist — this kills the old silent no-op (the regex matched nothing on a
 *      reformatted file yet the file was still rewritten + success logged).
 *   2. Decide idempotency on the parsed model (profile already a member, self-reg
 *      already enabled) so callers keep their existing skip semantics + messages.
 *   3. Mutate via a TARGETED string edit on the original text — NOT a full
 *      re-serialize. The XML declaration, the `xmlns` on <Network>,
 *      self-closing tags, and the file's existing indentation are preserved
 *      byte-for-byte, so a configured file re-run is a true no-op and there is
 *      zero deploy-diff hazard on this org-deployed file. (XMLBuilder/prettier
 *      are intentionally NOT used — a full re-serialize would churn formatting.)
 *      Profile names are asserted free of XML-special characters and interpolated
 *      raw — we reject such names rather than entity-escape them (a special
 *      character in a config-authored profile name signals a mistake).
 *
 * Pure (no fs / no process): org-setup.mjs reads/writes the file and owns the
 * per-call-site fail mode (throw StepError vs. loud console.error); these
 * helpers only parse, assert, and return the edited text. Kept in a dedicated
 * module so they carry automated coverage: the shipped SFDX package has no test
 * runner, so the specs live in the consuming ui-bundle-template-cli package
 * (patches-cli/test/unit/org-setup-xml.spec.ts) rather than bundling into every
 * generated app's dist/scripts.
 */

import { XMLParser } from 'fast-xml-parser';

const NETWORK_ROOT = 'Network';

/** Parser tuned to read the document faithfully: keep attributes, never coerce
 *  values (so `<selfRegistration>false</...>` stays the string "false"). */
const parser = new XMLParser({
  ignoreAttributes: false,
  parseTagValue: false,
  parseAttributeValue: false,
});

/**
 * Thrown when a required node is absent from the network metadata. Callers map
 * this to the fail mode appropriate to their orchestration position: the
 * post-deploy selfReg step rethrows it as a recorded StepError; the best-effort
 * pre-deploy prep logs it loudly without aborting.
 */
export class NetworkXmlError extends Error {}

/** Characters that would need XML entity-escaping if interpolated into markup. */
const XML_SPECIAL_CHARS = /[&<>"']/;

/**
 * Assert a profile name is safe to interpolate into the network metadata as-is.
 *
 * We deliberately do NOT entity-escape: a self-reg profile name is authored in
 * `org-setup.config.json`, and one containing `&`, `<`, `>`, or quotes almost
 * certainly signals a config mistake rather than a genuine name. Rather than
 * silently rewrite it into `&amp;`-style entities, fail loudly so the author
 * fixes the config. Throws NetworkXmlError (mapped by callers to their fail
 * mode) when the name contains an XML-special character.
 */
export function assertSafeProfileName(name) {
  if (XML_SPECIAL_CHARS.test(String(name))) {
    throw new NetworkXmlError(
      `profile name "${name}" contains an XML-special character (& < > " '); ` +
        `use a name without these characters in org-setup.config.json`,
    );
  }
  return String(name);
}

/**
 * Parse + assert this is a Network metadata document. Returns the parsed
 * `Network` object. Throws NetworkXmlError if the root is missing (e.g. a file
 * that is not actually network metadata).
 */
export function parseNetwork(xml) {
  let parsed;
  try {
    parsed = parser.parse(xml);
  } catch (e) {
    throw new NetworkXmlError(`network metadata is not well-formed XML: ${e.message}`);
  }
  const network = parsed?.[NETWORK_ROOT];
  if (network == null || typeof network !== 'object') {
    throw new NetworkXmlError(`expected a <${NETWORK_ROOT}> root node, but none was found`);
  }
  return network;
}

/** Normalize a fast-xml-parser child (absent | scalar | array) to an array. */
function asArray(node) {
  if (node == null) return [];
  return Array.isArray(node) ? node : [node];
}

/**
 * Indentation for a new <networkMemberGroups> child, derived from the file's
 * own formatting rather than a fixed width — so the targeted edit stays
 * byte-faithful on reformatted (e.g. 2-space) files, not just the shipped
 * 4-space template. Prefer an existing
 * sibling <profile>'s exact indent; otherwise fall back to the
 * <networkMemberGroups> indent doubled (it is always a direct child of the
 * <Network> root, i.e. one level deep).
 */
function memberGroupChildIndent(xml) {
  const sibling = xml.match(/\n([ \t]+)<profile>/);
  if (sibling) return sibling[1];
  const parent = xml.match(/\n([ \t]*)<networkMemberGroups>/);
  const parentIndent = parent ? parent[1] : '    ';
  return parentIndent + (parentIndent || '    ');
}

/**
 * Ensure `selfRegProfile` is listed under <networkMemberGroups>.
 *
 * Asserts <networkMemberGroups> exists (throws NetworkXmlError if not). Returns
 * `{ xml, changed }`: `changed: false` (input returned unchanged) when the
 * profile is already a member; otherwise the profile is inserted via a targeted
 * edit right after the opening <networkMemberGroups> tag and `changed: true`.
 */
export function addProfileToMemberGroups(xml, selfRegProfile) {
  const network = parseNetwork(xml);
  if (!('networkMemberGroups' in network) || network.networkMemberGroups == null) {
    throw new NetworkXmlError(
      'network metadata has no <networkMemberGroups> node to add the self-reg profile to',
    );
  }
  const existing = asArray(network.networkMemberGroups.profile).map((p) => String(p));
  if (existing.includes(String(selfRegProfile))) {
    return { xml, changed: false };
  }
  // Reject names with XML-special characters rather than escaping them (see
  // assertSafeProfileName) before interpolating raw.
  const safeName = assertSafeProfileName(selfRegProfile);
  // Targeted edit: insert after the open tag, matching the file's own member
  // indent (preserves formatting on reformatted files).
  const indent = memberGroupChildIndent(xml);
  const updated = xml.replace(
    /(<networkMemberGroups>)/,
    `$1\n${indent}<profile>${safeName}</profile>`,
  );
  return { xml: updated, changed: true };
}

/**
 * Enable self-registration: set <selfRegistration>true</selfRegistration> and
 * add <selfRegProfile>.
 *
 * Asserts <selfRegistration> exists (throws NetworkXmlError if not). Returns
 * `{ xml, changed }`: `changed: false` (input returned unchanged) when self-reg
 * is already enabled or a selfRegProfile is already present — same skip
 * semantics as before; otherwise applies a targeted edit and `changed: true`.
 */
export function enableSelfRegInXml(xml, selfRegProfile) {
  const network = parseNetwork(xml);
  if (!('selfRegistration' in network)) {
    throw new NetworkXmlError(
      'network metadata has no <selfRegistration> node to enable self-registration on',
    );
  }
  const alreadyEnabled = String(network.selfRegistration) === 'true';
  const alreadyHasProfile = 'selfRegProfile' in network;
  if (alreadyEnabled || alreadyHasProfile) {
    return { xml, changed: false };
  }
  // Reject names with XML-special characters rather than escaping them (see
  // assertSafeProfileName) before interpolating raw.
  const safeName = assertSafeProfileName(selfRegProfile);
  let updated = xml.replace(
    /<selfRegistration>false<\/selfRegistration>/,
    '<selfRegistration>true</selfRegistration>',
  );
  updated = updated.replace(
    /(\s*)(<selfRegistration>)/,
    `$1<selfRegProfile>${safeName}</selfRegProfile>\n$1$2`,
  );
  return { xml: updated, changed: true };
}
