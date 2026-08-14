/**
 * SObject response parser.
 *
 * Extracted verbatim from `searchService.ts`: the `RawSourceResult` interface
 * and the `edges → nodes / pageInfo / totalCount` mapping. Reads its subtree
 * from `root.uiapi.query[source.key]` and returns `null` when the alias is
 * absent (partial-failure leniency), never throwing.
 */

import type { SObjectSourceConfig, SourceResult } from "../../types";
import type { SourceRequest } from "../types";

interface RawSourceResult {
	edges?: Array<{ node?: unknown }> | null;
	pageInfo?: {
		hasNextPage?: boolean | null;
		hasPreviousPage?: boolean | null;
		startCursor?: string | null;
		endCursor?: string | null;
	} | null;
	totalCount?: number | null;
}

/**
 * Maps `root.uiapi.query[source.key]` (an `edges`/`pageInfo`/`totalCount`
 * subtree) to a {@link SourceResult}. Returns `null` when the alias is missing
 * from the response (e.g. a partial GraphQL error blanked this source only).
 */
export function parseSObjectResponse(
	root: Record<string, unknown>,
	request: SourceRequest<SObjectSourceConfig>,
): SourceResult | null {
	const queryRoot = (root?.uiapi as Record<string, unknown> | undefined)?.query as
		| Record<string, RawSourceResult | null | undefined>
		| undefined;

	const raw = queryRoot?.[request.source.key];
	if (raw == null) return null;

	const nodes = (raw.edges ?? [])
		.map((edge) => edge?.node)
		.filter((node): node is unknown => node != null);

	return {
		nodes,
		pageInfo: raw.pageInfo
			? {
					hasNextPage: raw.pageInfo.hasNextPage ?? false,
					hasPreviousPage: raw.pageInfo.hasPreviousPage ?? false,
					startCursor: raw.pageInfo.startCursor ?? null,
					endCursor: raw.pageInfo.endCursor ?? null,
				}
			: null,
		totalCount: raw.totalCount ?? null,
	};
}
