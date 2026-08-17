/**
 * CMS response parser: `root.managed_content.search.searchContentInChannels` →
 * {@link SourceResult}, normalising CMS offset paging onto the common
 * cursor-shaped {@link SourcePageInfo}.
 *
 * Partial-failure leniency: every level is guarded and the function returns
 * `null` — never throws — when its subtree is absent or errored.
 *
 * Offset → pageInfo:
 *   - `totalCount     = total`
 *   - `hasNextPage    = offset + items.length < total`
 *   - `hasPreviousPage= offset > 0`
 *   - `endCursor      = String(offset + pageSize)`  (the caller's request page size)
 *   - `startCursor    = String(offset)`
 */

import type { CmsSourceConfig, CmsSearchResponse } from "./types";
import type { SourceResult } from "../../types";
import type { SourceRequest } from "../types";

/** Narrows an unknown value to a plain object (or `undefined`). */
function asRecord(value: unknown): Record<string, unknown> | undefined {
	return value != null && typeof value === "object"
		? (value as Record<string, unknown>)
		: undefined;
}

/**
 * Reads the CMS subtree from the full response `data` root and maps it to a
 * {@link SourceResult}. Returns `null` when the subtree is absent/errored.
 *
 * `pageSize` for the cursor math is taken from the request (the page size we
 * asked for), matching `buildRequest`'s `$cmsLimit = request.pageSize`, so
 * next/prev advances the offset by exactly one page.
 */
export function parseCmsResponse(
	root: Record<string, unknown>,
	request: SourceRequest<CmsSourceConfig>,
): SourceResult | null {
	const managedContent = asRecord(root?.managed_content);
	const search = asRecord(managedContent?.search);
	const raw = asRecord(search?.searchContentInChannels);
	if (!raw) return null;

	const response = raw as unknown as CmsSearchResponse;

	const items = Array.isArray(response.items) ? response.items : [];
	const total = typeof response.total === "number" ? response.total : null;
	const offset = typeof response.offset === "number" ? response.offset : 0;
	const pageSize = request.pageSize;

	const hasNextPage = total != null ? offset + items.length < total : false;
	const hasPreviousPage = offset > 0;

	return {
		nodes: items,
		pageInfo: {
			hasNextPage,
			hasPreviousPage,
			startCursor: String(offset),
			endCursor: String(offset + pageSize),
		},
		totalCount: total,
	};
}
