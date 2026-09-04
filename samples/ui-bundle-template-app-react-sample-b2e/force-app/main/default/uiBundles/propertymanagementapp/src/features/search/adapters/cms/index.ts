/**
 * CMS adapter — fronts the `managed_content` GraphQL block behind the
 * kind-agnostic {@link SourceAdapter} contract.
 *
 * `buildRequest` is SYNCHRONOUS (the query builder is sync): it reads the
 * already-resolved `request.uiBundleId` (the caller resolves the async
 * `getUIBundleId()` upstream and threads it in), decodes `afterCursor` → offset,
 * and passes `request.contentTypes` through to the fragment builder ONLY when
 * non-empty (bootstrap omits them). `parseResponse` delegates to the CMS parser.
 *
 * The registry (`../registry.ts`) imports `cmsAdapter` from here by name.
 */

import type { CmsSourceConfig } from "./types";
import type { SourceAdapter, SourceRequest, QueryFragmentContribution } from "../types";
import { buildCmsQueryFragment } from "./cmsQueryFragment";
import { parseCmsResponse } from "./parseResponse";
import { isValidCmsFqn } from "./contentTypeUtils";

/** Decodes an opaque forward cursor into a non-negative integer offset. */
function decodeOffset(afterCursor: string | undefined): number {
	if (afterCursor == null) return 0;
	const parsed = parseInt(afterCursor, 10);
	if (!Number.isFinite(parsed) || parsed < 0) return 0;
	return parsed;
}

/**
 * Builds the CMS fragment contribution from a request. Content types are passed
 * through only when non-empty AND every entry is a valid FQN (defence in depth —
 * `useSearch` already validates before state).
 */
function buildCmsRequest(request: SourceRequest<CmsSourceConfig>): QueryFragmentContribution {
	const offset = decodeOffset(request.afterCursor);

	const contentTypes =
		Array.isArray(request.contentTypes) && request.contentTypes.length > 0
			? request.contentTypes.filter(isValidCmsFqn)
			: null;

	return buildCmsQueryFragment({
		keyword: request.q,
		uiBundleId: request.uiBundleId ?? "",
		offset,
		limit: request.pageSize,
		contentTypes: contentTypes && contentTypes.length > 0 ? contentTypes : null,
		language: request.language ?? null,
	});
}

export const cmsAdapter: SourceAdapter<CmsSourceConfig> = {
	kind: "cms",
	buildRequest: buildCmsRequest,
	parseResponse: parseCmsResponse,
};
