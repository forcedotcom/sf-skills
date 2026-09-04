/**
 * Connect REST caller for a CMS channel's searchable content types:
 *   GET /connect/cms/channels/{channelId}/searchable-content-types?page=N&pageSize=25
 * Returns the validated content types (FQN + server label) that populate the
 * content-type scope entries.
 */

import { connectGetJson, connectUrl, safeEncodePath } from "./apiUtils";
import {
	isValidCmsFqn,
	formatContentTypeLabel,
	type DiscoveredContentType,
} from "../contentTypeUtils";

/** Hard-coded REST page size. NEVER user input. */
const REST_PAGE_SIZE = 25;

/** Safety cap so a misbehaving backend cannot spin an unbounded loop. */
const MAX_PAGES = 100;

/** Channel id shape guard — `0ap` + 12–15 alphanumerics — validates the discovery channel id before the searchable-content-types REST call. */
export const CHANNEL_ID_PATTERN = /^0ap[a-zA-Z0-9]{12,15}$/;

/** One raw entry from the Connect response. */
interface RawContentTypeEntry {
	/** FQN with the `sfdc_cms__` prefix (e.g. "sfdc_cms__news"). */
	id?: string;
	/** Server-provided display name (e.g. "News"). */
	label?: string;
	/** Bare developer name without the prefix (e.g. "news"). */
	name?: string;
	// Legacy/alternate FQN field names kept as fallbacks.
	contentType?: string;
	fqn?: string;
	developerName?: string;
	isSearchable?: boolean;
	searchable?: boolean;
}

/** Loose shape of one page of the Connect response. */
interface RawContentTypesPage {
	items?: RawContentTypeEntry[];
	contentTypes?: RawContentTypeEntry[];
}

/** Reads the entries array from a page payload (array or object form). */
function pageItems(payload: unknown): RawContentTypeEntry[] {
	if (Array.isArray(payload)) return payload as RawContentTypeEntry[];
	const obj = payload as RawContentTypesPage | null;
	if (obj?.items && Array.isArray(obj.items)) return obj.items;
	if (obj?.contentTypes && Array.isArray(obj.contentTypes)) return obj.contentTypes;
	return [];
}

/** True when the entry is not explicitly marked non-searchable. */
function isSearchable(entry: RawContentTypeEntry): boolean {
	if (typeof entry.isSearchable === "boolean") return entry.isSearchable;
	if (typeof entry.searchable === "boolean") return entry.searchable;
	// No flag present → do not exclude on searchability (FQN validity still gates).
	return true;
}

/** ManagedContentType key prefix — the `id` custom content types carry instead of an FQN. */
const CONTENT_TYPE_RECORD_ID_PATTERN = /^0T1[a-zA-Z0-9]{12,15}$/;

/** Extracts the prefixed FQN from an entry, rebuilding `c__<name>` when `id` is a custom-type record id. */
function entryFqn(entry: RawContentTypeEntry): string | undefined {
	// Custom types put a ManagedContentType id in `id`; the FQN the GraphQL filter
	// accepts is `c__<name>`.
	if (entry.id && CONTENT_TYPE_RECORD_ID_PATTERN.test(entry.id)) {
		return entry.name ? `c__${entry.name}` : undefined;
	}
	return entry.id ?? entry.contentType ?? entry.fqn ?? entry.developerName;
}

/**
 * Fetches every searchable content type for `channelId`, paginating the
 * Connect endpoint until a short page is returned, then filtering to searchable
 * entries whose FQN passes `isValidCmsFqn`. Each result carries the FQN and the
 * server-provided display `label` (falling back to a derived label only when
 * the response omits one). De-duplicates by FQN, preserving first-seen order.
 *
 * @throws when `channelId` fails the shape guard (before any network call).
 */
export async function fetchSearchableContentTypes(
	channelId: string,
): Promise<DiscoveredContentType[]> {
	if (!CHANNEL_ID_PATTERN.test(channelId)) {
		throw new Error(`Invalid CMS channel id "${channelId}".`);
	}

	const encoded = safeEncodePath(channelId);
	const collected: DiscoveredContentType[] = [];
	const seen = new Set<string>();

	for (let page = 0; page < MAX_PAGES; page++) {
		const url = connectUrl(
			`/cms/channels/${encoded}/searchable-content-types?page=${page}&pageSize=${REST_PAGE_SIZE}`,
		);
		const payload = await connectGetJson(url);
		const items = pageItems(payload);

		for (const entry of items) {
			const fqn = entryFqn(entry);
			if (!fqn || !isSearchable(entry) || !isValidCmsFqn(fqn) || seen.has(fqn)) {
				continue;
			}
			seen.add(fqn);
			// Prefer the server label; fall back to a label derived from the FQN.
			const label = entry.label?.trim() || formatContentTypeLabel(fqn);
			collected.push({ fqn, label });
		}

		// Last page reached when fewer than a full page came back.
		if (items.length < REST_PAGE_SIZE) break;
	}

	return collected;
}
