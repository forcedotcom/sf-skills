/**
 * Executes a combined search request and parses each source's subtree via its
 * adapter, with partial-failure resilience.
 *
 * The combined GraphQL response can carry BOTH partial `data` AND `errors`
 * (`uiapi` and CMS `managed_content` are independent roots). Rather than
 * throwing on `response.errors`, we parse each source through
 * `getAdapter(kind).parseResponse(root, req)`:
 *   - a `SourceResult` → recorded in `results[key]`.
 *   - `null` (subtree absent/errored) → the source produced no data; if the
 *     request as a whole reported GraphQL errors, an attributed message is
 *     recorded in `errors[key]` so the UI can show a per-source error while
 *     sibling sources still render.
 *
 * Only a whole-request failure — the SDK call rejecting, or a response with no
 * `data` at all — throws, so `useSearch` surfaces it as a page-level error
 * (preserving the original network-failure behaviour).
 */

import { createDataSDK } from "@salesforce/platform-sdk";
import { buildSearchQuery } from "../queryBuilder";
import { getAdapter } from "../adapters/registry";
import type { SourceRequest } from "../adapters/types";
import type { SourceResult } from "../types";

/**
 * The outcome of a combined `runSearch`: successfully-parsed results plus a
 * per-source error map. `errors` is keyed by `source.key` and only carries an
 * entry for a source that failed to produce data (its subtree was absent or
 * errored). A source appears in at most one of `results` / `errors`.
 */
export interface RunSearchOutcome {
	results: Record<string, SourceResult>;
	errors: Record<string, string>;
}

/** Minimal shape of a GraphQL error we can attribute to a source by path. */
interface GraphQLErrorLike {
	message?: string | null;
	path?: Array<string | number> | null;
}

/**
 * Attributes GraphQL errors to a source by matching the error `path` against
 * the source's location in the document:
 *   - SObject aliases live under `uiapi.query.<key>`.
 *   - CMS lives under the root `managed_content` block.
 *
 * Returns the joined messages whose `path` matches `request`. When NO path
 * matches (or paths are absent), returns a GENERIC per-source message rather
 * than echoing unrelated sources' messages — otherwise one source could display
 * another's error text (over-broad cross-attribution). The whole-request
 * (`data == null`) path still joins ALL error messages; that lives in
 * `runSearch` and is unaffected.
 */
function attributeError(request: SourceRequest, errors: GraphQLErrorLike[]): string {
	const kind = request.source.kind;
	const key = request.source.key;

	const matched = errors.filter((e) => {
		const path = e.path;
		if (!path || path.length === 0) return false;
		if (kind === "cms") {
			return path[0] === "managed_content";
		}
		// SObject: uiapi -> query -> <key>
		return path[0] === "uiapi" && path[1] === "query" && path[2] === key;
	});

	// No path matched this source: don't leak sibling sources' messages — fall
	// back to a generic per-source explanation.
	if (matched.length === 0) {
		return "Search failed for this source.";
	}

	const message = matched
		.map((e) => e.message)
		.filter((m): m is string => !!m)
		.join("; ");
	return message || "Search failed for this source.";
}

/**
 * Runs one combined multi-source GraphQL request. Returns `{ results, errors }`
 * (never throws on partial GraphQL errors); throws only on a whole-request /
 * network failure.
 */
export async function runSearch(requests: SourceRequest[]): Promise<RunSearchOutcome> {
	const { document, variables } = buildSearchQuery(requests);

	const data = await createDataSDK();
	const response = await data.graphql!.query<unknown, Record<string, unknown>>({
		query: document,
		variables,
	});

	const root = response.data as Record<string, unknown> | undefined;
	const gqlErrors = (response.errors ?? []) as GraphQLErrorLike[];

	// Whole-request failure: no data at all. Surface as a page-level error
	// (preserves the original network-failure behaviour).
	if (root == null) {
		const message = gqlErrors
			.map((e) => e.message)
			.filter((m): m is string => !!m)
			.join("; ");
		throw new Error(message || "Unified search failed");
	}

	const results: Record<string, SourceResult> = {};
	const errors: Record<string, string> = {};

	for (const request of requests) {
		const key = request.source.key;
		let parsed: SourceResult | null = null;
		try {
			parsed = getAdapter(request.source.kind).parseResponse(root, request);
		} catch {
			// An adapter that throws while parsing its own subtree is a
			// per-source failure, not a page-level one.
			parsed = null;
		}

		if (parsed != null) {
			results[key] = parsed;
		} else if (gqlErrors.length > 0) {
			// No data for this source AND the request reported errors — attribute
			// a message so the UI can show a per-source error.
			errors[key] = attributeError(request, gqlErrors);
		}
		// else: no data and no errors — the source simply returned nothing;
		// leave it absent from both maps (empty result, no error).
	}

	return { results, errors };
}
