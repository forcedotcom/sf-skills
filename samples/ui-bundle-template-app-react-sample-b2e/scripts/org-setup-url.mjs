/**
 * Pure URL helpers for org-setup.mjs logout-URL productization.
 *
 * The platform requires an ABSOLUTE logout URL on Network metadata — a relative
 * value is rejected at deploy time ("The logout page URL must be an absolute
 * URL."). Apps ship a domain-INDEPENDENT, site-relative path in
 * org-setup.config.json (so the same value is valid on every org the app deploys
 * to); these helpers resolve it to an absolute URL at deploy time, against the
 * site's Experience Cloud origin discovered from the target org's communities.
 *
 * Pure (no fs / no process / no network): org-setup.mjs fetches the community list
 * (Connect API) and owns the fail modes; these helpers only classify + resolve
 * strings, so they carry automated coverage in the consuming test package
 * (org-setup-tests/test/org-setup-url.spec.ts). Companion to org-setup-xml.mjs.
 */

/** True when `value` is an absolute http(s) URL — already deployable as-is. */
export function isAbsoluteLogoutUrl(value) {
  return /^https?:\/\//i.test(String(value).trim());
}

/**
 * Leading path segment of a URL or path:
 *   "/propertyrentalapp/"                         -> "propertyrentalapp"
 *   "https://h.site.com/propertyrentalapp"        -> "propertyrentalapp"
 *   "/"                                           -> ""
 */
export function firstPathSegment(pathOrUrl) {
  let pathname;
  try {
    pathname = new URL(pathOrUrl).pathname; // absolute URL
  } catch {
    pathname = String(pathOrUrl).split(/[?#]/)[0]; // relative path
  }
  return pathname.replace(/^\/+/, '').split('/')[0];
}

/**
 * Choose the Experience Cloud community whose site URL should anchor a relative
 * logout path, and return its siteUrl (or null when none matches).
 *
 * Matches on the community's siteUrl PATH first — robust even when a community's
 * `urlPathPrefix` differs from its public path (e.g. a React "site container" site
 * whose companion ChatterNetwork carries a "…vforcesite" prefix), and correct on
 * custom domains where each site can have its own origin. Falls back to a
 * community whose `name` equals the derived site name. Does NOT fall back to an
 * arbitrary community: resolving against the wrong origin would silently produce a
 * valid-but-wrong absolute URL, so an unmatched relative path is left for the
 * caller to surface loudly.
 *
 * @param {Array<{name?: string, siteUrl?: string}>} communities
 * @param {string} configLogoutUrl  the site-relative path being resolved
 * @param {string} [siteName]
 * @returns {string|null} the matched community siteUrl
 */
export function pickCommunityBaseUrl(communities, configLogoutUrl, siteName) {
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

/**
 * Resolve a shipped logout-URL config value to an absolute URL.
 *   - already absolute      -> returned unchanged (trimmed).
 *   - site-relative path     -> resolved against `baseUrl` (a community siteUrl).
 *     Because the config path is root-relative ("/app/"), only baseUrl's ORIGIN is
 *     used, so any siteUrl on the same Experience Cloud domain yields the same
 *     result.
 *
 * Throws when a relative value has no baseUrl to resolve against, or when
 * resolution fails to produce an absolute http(s) URL.
 *
 * @param {string} configLogoutUrl
 * @param {string|null} baseUrl
 * @returns {string} an absolute URL
 */
export function resolveLogoutUrl(configLogoutUrl, baseUrl) {
  const value = String(configLogoutUrl).trim();
  if (isAbsoluteLogoutUrl(value)) return value;

  if (!baseUrl) {
    throw new Error(
      `logout URL "${configLogoutUrl}" is site-relative but no Experience Cloud ` +
        `community site URL was found to resolve it into an absolute URL`,
    );
  }
  let resolved;
  try {
    resolved = new URL(value, baseUrl).href;
  } catch (e) {
    throw new Error(
      `could not resolve logout URL "${configLogoutUrl}" against "${baseUrl}": ${e.message}`,
    );
  }
  if (!isAbsoluteLogoutUrl(resolved)) {
    throw new Error(`resolved logout URL "${resolved}" is not an absolute http(s) URL`);
  }
  return resolved;
}
