/**
 * Shared schema + validator for org-setup.config.json (W-23043729).
 *
 * Authored ONCE, used at TWO moments:
 *   (a) build / CI time — `scripts/validate-org-setup-config.mjs` validates every
 *       org-setup.config.json this repo ships, failing the build on any violation.
 *   (b) setup runtime — `org-setup.mjs` calls `validateConfig` once in main(),
 *       before any step runs, to catch the developer's local post-scaffold edits.
 *
 * `validateConfig` is pure: it parses + validates and RETURNS a result. Each call
 * site owns its own print/exit, so the build gate can report every bad file and
 * the runtime can exit immediately — and the validator stays unit-testable.
 *
 * The zod schema uses `.strict()` at every level so unknown keys (e.g. the
 * `permsetAssignment` singular typo) are rejected rather than silently ignored.
 */

import { z } from 'zod';

/** Closed set of assignee values — no arbitrary usernames. */
const Assignee = z.enum(['currentUser', 'guestUser', 'skip']);

// No siteName: for guestUser the site is derived from the single
// networks/<siteName>.network-meta.xml the app ships (see spec §5.2).
const Assignment = z
  .object({
    assignee: Assignee,
  })
  .strict();

export const ConfigSchema = z
  .object({
    permsetAssignments: z
      .object({
        // guestUser is valid here — siteName is derived, not per-assignment.
        defaultAssignee: Assignee.default('skip'),
        assignments: z.record(z.string(), Assignment).default({}),
      })
      .strict()
      .optional(),
    role: z
      .object({
        assignee: z.literal('currentUser'), // only value the role code honors
        roleName: z.string().min(1),
      })
      .strict()
      .optional(),
    selfRegistration: z
      .object({
        // No siteName: the site is derived from the single
        // networks/<siteName>.network-meta.xml the app ships (see spec §5.2),
        // exactly like the guestUser permset path.
        //
        // selfRegProfile also drives the M1 license pre-check (W-23043735):
        // setup derives the required UserLicense from this profile
        // (Profile.UserLicense, matched on the stable LicenseDefinitionKey) and
        // warns + skips self-registration when the org lacks it or has no seats.
        // No separate license field is declared — the requirement can't drift
        // from the profile the flow actually assigns.
        selfRegProfile: z.string().min(1),
        accountName: z.string().min(1),
      })
      .strict()
      .optional(),
    socialLogin: z
      .object({
        // Profile to add to NetworkMemberGroup so SSO-registered users can access
        // the community (e.g. "Customer Community User"). Also enables the
        // "Allow standard external profiles" org setting.
        communityMemberProfile: z.string().min(1),
        // DeveloperName of AuthProvider (OAuth) or SamlSsoConfig (SAML) records to link to the site's AuthConfig.
        // Required because React (Site Container) sites hide SSO config in Admin UI.
        authProviderNames: z.array(z.string().min(1)).min(1),
        // Permission set to assign to community users created via SSO.
        // Required because getCurrentUser() calls UI API GraphQL (uiapi.currentUser)
        // which needs API access (PermissionsApiEnabled) that the community profile lacks.
        // Typically the app's "*_Guest_User_Api_Access" permset.
        communityUserPermset: z.string().min(1).optional(),
      })
      .strict()
      .optional(),
    // URL members are redirected to after logging out, written to the site's
    // <logoutUrl> network metadata (a post-deploy step). Steers logout back to THIS
    // site so members aren't dropped on the org default-site login (which, in an
    // org hosting multiple sites, can be a different community). Prefer a
    // site-relative path (e.g. "/myapp/"): it is domain-independent, so the same
    // shipped value is valid on every org. The platform REQUIRES an absolute logout
    // URL, so org-setup resolves a relative path against the site's Experience Cloud
    // origin (discovered from the org at deploy time) before writing it; an
    // already-absolute value is used as-is. Kept a permissive non-empty string (not
    // z.string().url()) so relative paths are valid; character-safety for raw XML
    // interpolation is enforced at write time.
    logoutUrl: z.string().min(1).optional(),
  })
  .strict();

/**
 * Render a single zod issue as a "path: message" line. Empty path (a root-level
 * problem) renders as "<root>: message".
 */
function formatIssue(issue) {
  const path = issue.path.length > 0 ? issue.path.join('.') : '<root>';
  return `${path}: ${issue.message}`;
}

/**
 * Parse + validate a raw org-setup.config.json string.
 *
 * @param {string} rawText  raw file contents (not yet JSON-parsed)
 * @param {string} [configPath]  path used only for error messages
 * @returns {{ ok: true, data: object } | { ok: false, errors: string[] }}
 *   On success, `data` is the parsed + defaulted config. On failure, `errors`
 *   is a non-empty list of human-readable messages (JSON parse error or zod
 *   issues). The caller decides whether to print/exit.
 */
export function validateConfig(rawText, configPath) {
  const where = configPath ? ` (${configPath})` : '';

  let parsed;
  try {
    parsed = JSON.parse(rawText);
  } catch (err) {
    return { ok: false, errors: [`malformed JSON${where}: ${err.message}`] };
  }

  const result = ConfigSchema.safeParse(parsed);
  if (!result.success) {
    return { ok: false, errors: result.error.issues.map(formatIssue) };
  }

  return { ok: true, data: result.data };
}
