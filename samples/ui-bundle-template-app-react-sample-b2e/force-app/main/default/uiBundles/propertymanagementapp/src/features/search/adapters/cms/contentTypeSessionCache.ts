/**
 * `sessionStorage`-backed persistence for discovered CMS content types.
 *
 * Discovery is otherwise ephemeral: the in-memory module cache in
 * {@link useSearchableContentTypes} is wiped on a hard reload, and content
 * types are only re-derived once a CMS search actually returns a channel id.
 * Persisting them per channel lets the scope dropdown keep showing the
 * discovered types across any number of reloads, and lets the discovery hook
 * rehydrate them synchronously (no re-fetch) on mount.
 *
 * Two things are persisted:
 *   - `types:<channelId>`           — the validated `{ fqn, label }[]` for that
 *     channel. Keyed by the channel id, which is channel-specific already.
 *   - `last-channel-id:<uiBundleId>` — the most recently discovered channel id
 *     FOR THAT UIBundle, so the hook can seed its discovery state on mount
 *     before any CMS result arrives. Keyed by UIBundle id (not origin-wide):
 *     content types are channel-specific, so a second UIBundle opened in the
 *     same session must NOT inherit the first bundle's channel/types.
 *
 * Every access is wrapped: `sessionStorage` can be absent (SSR), throw
 * (private-mode / disabled cookies), or hold corrupt JSON. On any failure we
 * degrade to "no cache" rather than surfacing an error — persistence is an
 * enhancement, never a hard dependency.
 */

import { isValidCmsFqn, type DiscoveredContentType } from "./contentTypeUtils";
import { CHANNEL_ID_PATTERN } from "./api/searchableContentTypesService";
import { UI_BUNDLE_ID_PATTERN } from "./searchChannel";

const KEY_PREFIX = "cms-search:content-types:";
const TYPES_KEY = (channelId: string) => `${KEY_PREFIX}types:${channelId}`;
const LAST_CHANNEL_KEY = (uiBundleId: string) => `${KEY_PREFIX}last-channel-id:${uiBundleId}`;

/** Returns the `sessionStorage` object, or `null` when it is unavailable/throws. */
function storage(): Storage | null {
	try {
		if (typeof sessionStorage === "undefined") return null;
		return sessionStorage;
	} catch {
		// Accessing `sessionStorage` can throw when storage is disabled.
		return null;
	}
}

/** Narrows an unknown parsed value to a clean `DiscoveredContentType[]`. */
function sanitize(parsed: unknown): DiscoveredContentType[] {
	if (!Array.isArray(parsed)) return [];
	const out: DiscoveredContentType[] = [];
	const seen = new Set<string>();
	for (const entry of parsed) {
		if (!entry || typeof entry !== "object") continue;
		const { fqn, label } = entry as { fqn?: unknown; label?: unknown };
		// Re-validate the FQN on read: cached data is untrusted input and its
		// values flow straight into the query variable and rendered labels.
		if (typeof fqn !== "string" || !isValidCmsFqn(fqn) || seen.has(fqn)) continue;
		if (typeof label !== "string" || label.length === 0) continue;
		seen.add(fqn);
		out.push({ fqn, label });
	}
	return out;
}

/**
 * Reads the persisted content types for `channelId`. Returns `null` when there
 * is no (valid) cache entry, so callers can distinguish "never persisted" from
 * "persisted as empty".
 */
export function readCachedContentTypes(channelId: string): DiscoveredContentType[] | null {
	const store = storage();
	if (!store || !CHANNEL_ID_PATTERN.test(channelId)) return null;
	let raw: string | null;
	try {
		raw = store.getItem(TYPES_KEY(channelId));
	} catch {
		return null;
	}
	if (raw == null) return null;
	try {
		return sanitize(JSON.parse(raw));
	} catch {
		return null;
	}
}

/**
 * Persists `types` for `channelId`. No-ops (never throws) when storage is
 * unavailable or the id is malformed. The last-discovered-channel pointer is
 * written separately via {@link writeLastChannelId}, which needs the UIBundle
 * id this channel belongs to.
 */
export function writeCachedContentTypes(channelId: string, types: DiscoveredContentType[]): void {
	const store = storage();
	if (!store || !CHANNEL_ID_PATTERN.test(channelId)) return;
	try {
		store.setItem(TYPES_KEY(channelId), JSON.stringify(types));
	} catch {
		// Quota exceeded / disabled storage — persistence is best-effort.
	}
}

/**
 * Records `channelId` as the last discovered channel FOR `uiBundleId`. Keyed by
 * UIBundle id so a different bundle opened in the same session never inherits
 * this channel. No-ops (never throws) when storage is unavailable or either id
 * is malformed.
 */
export function writeLastChannelId(uiBundleId: string, channelId: string): void {
	const store = storage();
	if (!store || !UI_BUNDLE_ID_PATTERN.test(uiBundleId) || !CHANNEL_ID_PATTERN.test(channelId)) {
		return;
	}
	try {
		store.setItem(LAST_CHANNEL_KEY(uiBundleId), channelId);
	} catch {
		// Quota exceeded / disabled storage — persistence is best-effort.
	}
}

/**
 * Returns the last discovered channel id for `uiBundleId` (validated shape), or
 * `null`. Lets the discovery hook seed its channel on mount so THIS bundle's
 * cached types render immediately, before any CMS search result comes back.
 */
export function readLastChannelId(uiBundleId: string): string | null {
	const store = storage();
	if (!store || !UI_BUNDLE_ID_PATTERN.test(uiBundleId)) return null;
	let raw: string | null;
	try {
		raw = store.getItem(LAST_CHANNEL_KEY(uiBundleId));
	} catch {
		return null;
	}
	return raw != null && CHANNEL_ID_PATTERN.test(raw) ? raw : null;
}
