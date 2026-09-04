/**
 * CMS content-type FQN helpers.
 *
 * `isValidCmsFqn` / `CMS_FQN_PATTERN` guard every FQN before it enters query
 * state, the GraphQL variable, or a rendered label. `formatContentTypeLabel`
 * turns an FQN into a human-readable dropdown/section label.
 */

/**
 * Formats a CMS content type FQN into a human-readable label.
 * Strips the "sfdc_cms__" (OOTB) or "c__" (custom) prefix, splits camelCase, title-cases each word.
 *
 * Examples:
 *   "sfdc_cms__blogPost" → "Blog Post"
 *   "sfdc_cms__news" → "News"
 *   "c__NewsArticle" → "News Article"
 *   "c__Recipe" → "Recipe"
 */
export function formatContentTypeLabel(fqn: string): string {
	const stripped = fqn.replace(/^(?:sfdc_cms__|c__)/, "");
	const words = stripped.replace(/([a-z])([A-Z])/g, "$1 $2");
	return words.charAt(0).toUpperCase() + words.slice(1);
}

// OOTB content types are namespaced `sfdc_cms__<name>`; custom types created in
// a namespace-less org take the default `c__<name>` prefix. Both are valid FQNs.
export const CMS_FQN_PATTERN = /^(?:sfdc_cms__|c__)[a-zA-Z][a-zA-Z0-9]{0,39}$/;

export function isValidCmsFqn(fqn: string): boolean {
	return CMS_FQN_PATTERN.test(fqn);
}

/**
 * A discovered CMS content type: its FQN (`sfdc_cms__…`, used as the scope value
 * and query filter) and its server-provided display `label` (e.g. "News").
 */
export interface DiscoveredContentType {
	fqn: string;
	label: string;
}
