/**
 * CMS content-type FQN helpers.
 *
 * `isValidCmsFqn` / `CMS_FQN_PATTERN` guard every FQN before it enters query
 * state, the GraphQL variable, or a rendered label. `formatContentTypeLabel`
 * turns an FQN into a human-readable dropdown/section label.
 */

/**
 * Formats a CMS content type FQN into a human-readable label.
 * Strips "sfdc_cms__" prefix, splits camelCase, title-cases each word.
 *
 * Examples:
 *   "sfdc_cms__blogPost" → "Blog Post"
 *   "sfdc_cms__news" → "News"
 *   "sfdc_cms__document" → "Document"
 *   "sfdc_cms__pressRelease" → "Press Release"
 */
export function formatContentTypeLabel(fqn: string): string {
	const stripped = fqn.replace(/^sfdc_cms__/, "");
	const words = stripped.replace(/([a-z])([A-Z])/g, "$1 $2");
	return words.charAt(0).toUpperCase() + words.slice(1);
}

export const CMS_FQN_PATTERN = /^sfdc_cms__[a-zA-Z][a-zA-Z0-9]{0,39}$/;

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
