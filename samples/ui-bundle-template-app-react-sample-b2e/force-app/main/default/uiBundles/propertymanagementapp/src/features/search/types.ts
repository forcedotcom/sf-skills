/**
 * Configuration types for unified (multi-source) search.
 *
 * The application developer declares a SearchConfig with one entry per
 * searchable backend. Today every source is an SObject queried via the uiapi
 * GraphQL bridge; future adapters (CMS, REST, etc.) can plug in by introducing
 * a new `kind` and a matching runtime adapter without changing any consumer.
 *
 * The library handles query construction, filter/sort/pagination state, URL
 * sync, and result fan-out. The application owns rendering and routing.
 */

import type { FilterFieldConfig, ActiveFilterValue } from "./utils/filterUtils";
import type { SortFieldConfig, SortState } from "./utils/sortUtils";
import type { CmsSourceConfig } from "./adapters/cms/types";
import type { DiscoveredContentType } from "./adapters/cms/contentTypeUtils";

// Re-export the CMS source config so consumers can import it from the public
// type surface without reaching into `adapters/cms`.
export type { CmsSourceConfig };

/**
 * A single field to include in the GraphQL selection set of an SObject source.
 *
 * - `"Name"` (string shorthand): emits `Name @optional { value displayValue }`.
 * - `{ name, subfields }`: emits a nested selection (relationship traversal).
 * - `{ name, raw: true }`: emits the bare field name (e.g. for Id-like fields
 *   that are not wrapped in `{ value displayValue }`).
 *
 * The configured `idField` (default: "Id") is added automatically; do not list
 * it explicitly.
 */
export type DisplayField =
	| string
	| { name: string; raw: true }
	| { name: string; subfields: DisplayField[] };

/** Configuration for one SObject source in a search experience. */
export interface SObjectSourceConfig {
	/** Discriminator — selects the runtime adapter. */
	kind: "sobject";
	/**
	 * Stable identifier. Used as the GraphQL alias, the URL namespace, and the
	 * result-map key. Must match `/^[A-Za-z_][A-Za-z0-9_]*$/`.
	 */
	key: string;
	/** GraphQL object name (e.g. "Account", "Contact"). */
	objectName: string;
	/**
	 * Plural display label — used in section headers, the scope dropdown, and
	 * empty-state messages (e.g. "Accounts", "Maintenance Requests").
	 */
	label: string;
	/**
	 * Singular display label for a single record of this type (e.g. "Account",
	 * "Maintenance Request"). Used for the per-card source badge in the merged
	 * grid. Falls back to `label` when omitted.
	 */
	labelSingular?: string;
	/** Field name that uniquely identifies a record. Defaults to "Id". */
	idField?: string;
	/**
	 * URL pattern used by the default renderer to build a result link.
	 *
	 * Tokens of the form `:fieldName` are replaced with the corresponding
	 * field's value at render time (e.g. `:id` resolves to the record's
	 * `idField` value, `:Name` resolves to the Name field's `value`).
	 *
	 * Example: `"/accounts/:id"` produces `<Link to="/accounts/001xx0000003DGb">`.
	 *
	 * Optional — when omitted, the default renderer emits non-clickable rows.
	 */
	routePattern?: string;
	/**
	 * Fields the global `q` term should match against.
	 * Built into an `or` of `like %q%`. Supports dot-notation for relationship
	 * fields (e.g. "Owner.Name").
	 */
	searchableFields: string[];
	/**
	 * Fields to include in the GraphQL selection set. The id field is added
	 * automatically; do not list it.
	 */
	displayFields: DisplayField[];
	/**
	 * Optional structured filters for this source.
	 *
	 * Named `filterBy` (rather than "the filters shown in the panel") because a
	 * future entry may constrain the query without rendering a control — e.g. a
	 * default `Status != Completed` that hides completed items from results while
	 * never appearing in the UI. Today every entry renders an input via
	 * `DefaultFilterPanel`.
	 */
	filterBy?: FilterFieldConfig[];
	/** Optional sort options surfaced in the per-source sort dropdown. */
	sortBy?: SortFieldConfig[];
	/** Initial sort applied when no URL sort is present. */
	defaultSort?: SortState;
	/**
	 * GraphQL type name for the `where` variable.
	 * Defaults to `${objectName}_Filter` — override only for non-conventional schemas.
	 */
	whereTypeName?: string;
	/** GraphQL type name for the `orderBy` variable. Defaults to `${objectName}_OrderBy`. */
	orderByTypeName?: string;
}

/**
 * Discriminated union of every source kind a search experience can query.
 *
 * The `kind` field selects the runtime adapter (see `adapters/registry.ts`) and
 * narrows the config to the fields that kind understands. New backends extend
 * this union with a new `kind` + a matching adapter — no consumer changes.
 *
 * `CmsSourceConfig` is authored in `adapters/cms/types.ts` and unioned here so
 * `SourceConfig` remains the single kind-agnostic config type.
 */
export type SourceConfig = SObjectSourceConfig | CmsSourceConfig;

/**
 * One global pagination config for the whole search experience. It is the
 * single source of truth — there is no per-source pagination. The same
 * `pageSize` / `pageSizeOptions` apply across every object type and in every
 * scope, including single-object pages (`restrictTo` / `lockedScope`) and when
 * the scope dropdown narrows to one source.
 */
export interface SearchPaginationConfig {
	/**
	 * How results are paginated:
	 *   - `"per-source"` (default): each source advances its own cursor; a page
	 *     can hold up to `sources × pageSize` items. This is what the drop-in
	 *     `<Search>` (one section per source) expects.
	 *   - `"merged"`: treat the cumulative result set as one list and window it
	 *     into fixed pages of `pageSize`. Each page shows exactly `pageSize` items
	 *     across all sources — use for a single combined grid.
	 */
	mode?: "per-source" | "merged";
	/**
	 * In `"merged"` mode, how nodes from different sources are ordered:
	 *   - `"sequential"` (default): source 1 in full, then source 2, …
	 *   - `"interleaved"`: round-robin — every source gets equal priority.
	 *   - `"proportional"`: each source spread by its result count, so larger
	 *     sources appear more often. Ignored in `"per-source"` mode.
	 */
	mergeOrder?: "sequential" | "interleaved" | "proportional";
	/** Items per page (across all sources in `"merged"` mode; per source otherwise). */
	pageSize: number;
	/** Page sizes offered in the "results per page" control. */
	pageSizeOptions: number[];
}

/** Top-level config passed to {@link useSearch}. */
export interface SearchConfig {
	sources: SourceConfig[];
	/**
	 * Global pagination config — the single source of truth for page size, page
	 * options, mode, and merge order. See {@link SearchPaginationConfig}. When
	 * omitted, pagination defaults to per-source mode, page size 10, options
	 * `[10, 25, 50]`.
	 */
	pagination?: SearchPaginationConfig;
}

// ---------------------------------------------------------------------------
// Runtime types
// ---------------------------------------------------------------------------

export interface SourcePageInfo {
	hasNextPage: boolean;
	hasPreviousPage: boolean;
	endCursor: string | null;
	startCursor: string | null;
}

/**
 * Per-source result. Nodes are typed as `unknown` at the library boundary —
 * the application narrows them in its `renderResult` callback (typically by
 * casting to a codegen-generated node type).
 */
export interface SourceResult {
	nodes: unknown[];
	pageInfo: SourcePageInfo | null;
	totalCount: number | null;
}

export interface SourceController {
	/**
	 * The source's config. Widened to the `SourceConfig` union so a controller
	 * can front any kind (SObject, CMS, …); consumers narrow on `config.kind`
	 * before reading kind-specific fields (`objectName`, `filterBy`, `sortBy`, …).
	 */
	config: SourceConfig;
	result: SourceResult | null;
	loading: boolean;
	error: string | null;
	filters: {
		active: ActiveFilterValue[];
		set: (field: string, value: ActiveFilterValue | undefined) => void;
		remove: (field: string) => void;
	};
	sort: {
		current: SortState | null;
		set: (sort: SortState | null) => void;
	};
	pagination: {
		pageSize: number;
		/** Allowed page sizes — from the global pagination config. */
		pageSizeOptions: readonly number[];
		pageIndex: number;
		hasNextPage: boolean;
		hasPreviousPage: boolean;
		setPageSize: (size: number) => void;
		goToNextPage: () => void;
		goToPreviousPage: () => void;
	};
}

/**
 * The currently-selected search scope. Grammar:
 *
 * ```
 * scope = "all" | <sobjectKey> | <cmsKey> | "<cmsKey>:<contentTypeFqn>"
 * ```
 *
 * - `"all"`: every source in the config is queried and rendered.
 * - `<sobjectKey>` / `<cmsKey>`: only that source is queried and rendered; the
 *   combined query still runs (a CMS source in scope sends its discovered
 *   content types if any are known, else omits them on the bootstrap call).
 * - `"<cmsKey>:<contentTypeFqn>"`: a **CMS-only** search narrowed to one content
 *   type — SObject sources are dropped from the request and the CMS fragment
 *   sends `contentTypes = [<fqn>]`. `<fqn>` must pass `isValidCmsFqn`. These
 *   entries are appended to the scope dropdown after content-type discovery.
 *
 * The `":"` separator disambiguates the two halves; source keys match
 * `/^[A-Za-z_][A-Za-z0-9_]*$/` (no colon), and FQNs match `CMS_FQN_PATTERN`.
 */
export type SearchScope = "all" | string;

export const ALL_SCOPE = "all" as const;

/** Separator between a CMS source key and a content-type FQN in a scope value. */
export const CMS_SCOPE_SEPARATOR = ":" as const;

/**
 * A parsed {@link SearchScope}. `base` is the plain scope (`"all"` or a source
 * key); `cmsFqn` is the selected CMS content-type FQN when the scope carries the
 * `"<cmsKey>:<fqn>"` form, else `undefined`.
 */
export interface ParsedScope {
	base: SearchScope;
	cmsFqn?: string;
}

/**
 * Splits a {@link SearchScope} into `{ base, cmsFqn }`. Only the first `":"`
 * separates the CMS source key from the content-type FQN; source keys contain
 * no colon and FQNs (`sfdc_cms__…`) contain no colon either, so a single split
 * is unambiguous. A scope with no separator has `cmsFqn === undefined`.
 */
export function parseScope(scope: SearchScope): ParsedScope {
	const sep = scope.indexOf(CMS_SCOPE_SEPARATOR);
	if (sep === -1) return { base: scope };
	return { base: scope.slice(0, sep), cmsFqn: scope.slice(sep + 1) };
}

/**
 * One result node tagged with the source it came from. Produced by
 * {@link SearchHandle.mergedResults} so a single combined grid can render
 * cross-source results and still pick the right card per node.
 */
export interface MergedResultItem {
	/** The `key` of the source this node came from. */
	sourceKey: string;
	/** The raw result node (cast to your typed node in the renderer). */
	node: unknown;
}

/**
 * Aggregate pagination across every in-scope source, exposed by
 * {@link SearchHandle.globalPagination}. Its exact behaviour depends on the
 * `pagination` mode passed to {@link useSearch}:
 *
 * - **`"merged"`** (recommended for a single combined grid): the cumulative
 *   result set is treated as one list and windowed into fixed pages of
 *   `pageSize`. Page `P` always shows **exactly** `pageSize` items (the last
 *   page may show fewer), `pageCount` is `ceil(totalCount / pageSize)`, and
 *   `goToPage` can jump to any page. Under the hood each in-scope source fetches
 *   `(P + 1) * pageSize` rows from its front, the results are concatenated in
 *   config order, and the page-`P` slice is taken — so the math is exact, not an
 *   estimate.
 * - **`"per-source"`** (default): each source paginates with its own cursor and
 *   a "global page" is the furthest-advanced in-scope source's page. `Next`
 *   advances only the sources still on the current global page that have more
 *   data; a source that runs out is left behind. `goToPage` is best-effort
 *   (adjacent pages only) because cursors can't seek to an arbitrary offset.
 */
export interface GlobalPagination {
	/** Current global page, 0-based. */
	pageIndex: number;
	/**
	 * Total number of global pages. In `"merged"` mode this is exactly
	 * `ceil(totalCount / pageSize)`. In `"per-source"` mode it is the `max` over
	 * in-scope sources of `ceil(totalCount / pageSize)` and may be an estimate if
	 * a source omits `totalCount`. `0` when there are no results, otherwise `>= 1`.
	 */
	pageCount: number;
	/** Shared page size. */
	pageSize: number;
	/** Allowed page sizes (from the first in-scope source). */
	pageSizeOptions: readonly number[];
	/** True when there is a page after the current one. */
	hasNextPage: boolean;
	/** True when the current global page is past the first. */
	hasPreviousPage: boolean;
	/** Cumulative result count summed across in-scope sources. */
	totalCount: number;
	/** Advance to the next global page. */
	goToNextPage: () => void;
	/** Step back to the previous global page. */
	goToPreviousPage: () => void;
	/**
	 * Jump to a specific 0-based page. Exact in `"merged"` mode; in
	 * `"per-source"` mode only adjacent pages are honoured (others are a no-op).
	 */
	goToPage: (pageIndex: number) => void;
	/** Set the page size (resets to the first page). */
	setPageSize: (size: number) => void;
}

export interface SearchHandle {
	q: string;
	setQ: (q: string) => void;
	scope: SearchScope;
	setScope: (scope: SearchScope) => void;
	/**
	 * True when the caller passed `lockedScope` to `useSearch`. Consumers
	 * should hide the scope dropdown and read-only display the locked source.
	 */
	scopeLocked: boolean;
	sources: Record<string, SourceController>;
	/**
	 * Source controllers that participate in the current scope, in config
	 * declaration order. In `"all"` scope this is every source; otherwise just
	 * the selected one. Convenience for callers building aggregate UI.
	 */
	inScopeSources: SourceController[];
	/**
	 * In-scope nodes flattened into one list (config order, source by source),
	 * each tagged with its `sourceKey` — for rendering a single combined grid
	 * instead of one section per source. In `"merged"` pagination mode this is
	 * exactly the current page's window (at most `globalPagination.pageSize`
	 * items); in `"per-source"` mode it is every in-scope source's current page
	 * concatenated.
	 */
	mergedResults: MergedResultItem[];
	/**
	 * Aggregate pagination across all in-scope sources — drive one shared
	 * pager over the cumulative result set. See {@link GlobalPagination}.
	 */
	globalPagination: GlobalPagination;
	loading: boolean;
	error: string | null;
	/**
	 * CMS content types discovered at runtime from the CMS channel — each with
	 * its FQN and server-provided display `label` (empty until the first CMS
	 * result yields a channel id and discovery completes). The scope dropdown
	 * appends a `"<cmsKey>:<fqn>"` entry per type so a user can narrow a CMS
	 * search to a single content type. Empty for SObject-only configs or before
	 * discovery.
	 */
	discoveredContentTypes: DiscoveredContentType[];
	resetAll: () => void;
}

/** Type alias for a render callback per source key. */
export type RenderResultFn = (sourceKey: string, node: unknown) => React.ReactNode;
