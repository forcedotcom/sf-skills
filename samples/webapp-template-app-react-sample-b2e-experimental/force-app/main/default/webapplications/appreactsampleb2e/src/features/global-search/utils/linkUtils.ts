/**
 * Shared allowlist for link protocols (e.g. for FormattedUrl, and future mailto/tel if rendered as links).
 * Centralizes protocol checks so new link types can be added in one place.
 */
export const ALLOWED_LINK_PROTOCOLS = ["http:", "https:"] as const;

export function isAllowedLinkUrl(value: string): boolean {
	try {
		const u = new URL(value);
		return (ALLOWED_LINK_PROTOCOLS as readonly string[]).includes(u.protocol);
	} catch {
		return false;
	}
}
