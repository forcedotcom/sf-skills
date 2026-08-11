/**
 * Executes a search request and parses results into a per-source map.
 *
 * Today there's only one adapter — SObjects via the platform-sdk uiapi GraphQL
 * bridge. Future adapters (CMS, REST, etc.) can run alongside this one and
 * have their results merged into the same `Record<sourceKey, SourceResult>`
 * by the hook.
 */

import { createDataSDK } from "@salesforce/platform-sdk";
import { buildSearchQuery, type SourceRequest } from "../queryBuilder";
import type { SourceResult } from "../types";

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
 * Runs a single multi-aliased GraphQL request against uiapi.query.
 *
 * Returns a plain object keyed by source.key. A source whose alias is missing
 * from the response (e.g. due to a partial GraphQL error) is omitted; the
 * caller can detect this by `result[sourceKey] == null`.
 */
export async function runSearch(requests: SourceRequest[]): Promise<Record<string, SourceResult>> {
	const { document, variables } = buildSearchQuery(requests);

	const data = await createDataSDK();
	const response = await data.graphql!.query<unknown, Record<string, unknown>>({
		query: document,
		variables,
	});

	if (response.errors?.length) {
		throw new Error(response.errors.map((e) => e.message).join("; "));
	}

	const root = response.data as Record<string, unknown> | undefined;
	const queryRoot = (root?.uiapi as Record<string, unknown> | undefined)?.query as
		| Record<string, RawSourceResult | null | undefined>
		| undefined;

	const out: Record<string, SourceResult> = {};
	for (const request of requests) {
		const raw = queryRoot?.[request.source.key];
		if (raw == null) continue;
		const nodes = (raw.edges ?? [])
			.map((edge) => edge?.node)
			.filter((node): node is unknown => node != null);
		out[request.source.key] = {
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
	return out;
}
