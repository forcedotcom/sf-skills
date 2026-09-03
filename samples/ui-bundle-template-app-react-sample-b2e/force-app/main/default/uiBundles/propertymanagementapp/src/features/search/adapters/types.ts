/**
 * Kind-agnostic adapter contracts for unified (multi-source) search.
 *
 * Every searchable backend ("sobject", "cms", …) is fronted by a
 * {@link SourceAdapter}. The core query builder and result parser are
 * completely kind-agnostic: they dispatch to the adapter registered for a
 * source's `kind`, so a new backend plugs in by adding a `kind` + an adapter,
 * never by touching the common builder/parser or any consumer.
 *
 *  - {@link SourceAdapter.buildRequest} contributes a {@link QueryFragmentContribution}
 *    (its GraphQL fragment, variable declarations, and variable values) that the
 *    builder assembles into one combined document.
 *  - {@link SourceAdapter.parseResponse} receives the full response `data` root
 *    and extracts this source's `SourceResult`, returning `null` (never
 *    throwing) when its own subtree is absent or errored — this is what lets
 *    sources fail independently (partial-failure resilience).
 */

import type { SourceConfig, SourceResult } from "../types";
import type { ActiveFilterValue } from "../utils/filterUtils";
import type { SortState } from "../utils/sortUtils";

/**
 * One source's contribution to the combined GraphQL document.
 *
 * The builder concatenates every source's `variableDeclarations` into the
 * `query Search(...)` header and merges every source's `variables` into one
 * flat map. Fragments are placed by `placement`:
 *   - `"uiapi.query"` → inside the shared `uiapi { query { … } }` block.
 *   - `"root"`        → a sibling of `uiapi` at the document root (e.g. the CMS
 *     `managed_content { … }` block).
 *
 * A contribution MAY declare zero extra variables (e.g. the CMS bootstrap call
 * omits `$cmsContentTypeFQNs` entirely). The builder handles declaration lists of
 * differing lengths, so an unused/undeclared variable is never emitted.
 */
export interface QueryFragmentContribution {
	/** Namespaced GraphQL variable declarations, e.g. `"$cmsKeyword: String!"`. */
	variableDeclarations: string[];
	/** Values for the declared variables, keyed by (unprefixed) variable name. */
	variables: Record<string, unknown>;
	/** Where the `fragment` is spliced into the combined document. */
	placement: "uiapi.query" | "root";
	/** The GraphQL selection fragment (unindented; the builder indents it). */
	fragment: string;
}

/**
 * A per-source search request. Generic over the source config so an adapter can
 * narrow to its own config kind (e.g. `SourceRequest<CmsSourceConfig>`).
 *
 * The base fields (`source`/`q`/`filters`/`sort`/`pageSize`/`afterCursor`) are
 * kind-agnostic. The trailing fields are optional and only populated for the
 * kinds that need them; the sync query builder never resolves async values, so
 * anything async (e.g. the CMS UIBundle id) is resolved by the caller and
 * threaded in here.
 */
export interface SourceRequest<T extends SourceConfig = SourceConfig> {
	/** The config for the source this request targets. */
	source: T;
	/** The global search term, broadcast to every source. */
	q: string;
	/** Active structured filters (SObject-relevant; other kinds may ignore). */
	filters: ActiveFilterValue[];
	/** Active sort (SObject-relevant; other kinds may ignore). */
	sort: SortState | null;
	/** Page size for this fetch (validated against `pageSizeOptions` upstream). */
	pageSize: number;
	/** Opaque forward cursor for this fetch (CMS decodes it to an offset). */
	afterCursor: string | undefined;
	/**
	 * CMS-only, optional. Present (non-null, non-empty) only when content types
	 * are known/selected; absent on the bootstrap call so the CMS adapter omits
	 * `$cmsContentTypeFQNs` entirely.
	 */
	contentTypes?: string[] | null;
	/**
	 * CMS-only, optional. The resolved UIBundle id fed into the CMS search
	 * query. Resolved by the caller (async `getUIBundleId()`) BEFORE the sync
	 * query builder runs, then threaded in here so `buildRequest` stays
	 * synchronous. Ignored by non-CMS adapters.
	 */
	uiBundleId?: string;
	/** CMS-only, optional. The current user's language tag fed to the CMS search `language` argument. */
	language?: string;
}

/**
 * Runtime adapter for one source `kind`. Bridges a kind-agnostic
 * {@link SourceRequest} to a GraphQL fragment and back to a {@link SourceResult}.
 */
export interface SourceAdapter<T extends SourceConfig = SourceConfig> {
	/** The `kind` discriminator this adapter handles. */
	readonly kind: T["kind"];
	/** Build this source's fragment/variables contribution for the combined doc. */
	buildRequest(request: SourceRequest<T>): QueryFragmentContribution;
	/**
	 * Extract this source's result from the full response `data` root. Returns
	 * `null` when the source's own subtree is absent or errored — never throws
	 * for a partial failure.
	 */
	parseResponse(root: Record<string, unknown>, request: SourceRequest<T>): SourceResult | null;
}
