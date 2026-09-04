/**
 * Merged results layout — a single combined grid across every in-scope source,
 * driven by one global pager over the cumulative result set.
 *
 * This is the counterpart to {@link SearchResults} (which renders one stacked
 * section per source). Use it when you want a unified "search everything" grid:
 * heterogeneous cards laid out together, one shared pagination control, and a
 * single results count — the layout the drop-in `<Search>` renders when the
 * config sets `pagination.mode: "merged"`, and the same shape most apps
 * hand-build on top of `useSearch`.
 *
 * It reads three aggregate accessors off the {@link SearchHandle}
 * (`mergedResults`, `globalPagination`, `inScopeSources`), so it honours the
 * config's `pagination.mode` / `mergeOrder` automatically. For a true combined
 * grid, pair it with `pagination.mode: "merged"` (see the feature README, §9).
 *
 * Layout, top to bottom:
 *   - **Single-source filter chrome** — when the scope is narrowed to one
 *     source (selected or `lockedScope`), that source's filter panel + sort +
 *     active-filter chips render here. Under "All", per-source filters can't be
 *     combined across heterogeneous objects, so this row is omitted.
 *   - **Results count** — the cumulative in-scope total, on its own row directly
 *     above the grid, in every scope. Hidden when there are no results.
 *   - **The grid** — one card per `mergedResults` item, rendered via the
 *     per-source `renderResult[sourceKey]` callback. In a mixed grid (2+ sources
 *     in scope) each card is topped with an auto source badge — the source's
 *     `labelSingular` (falling back to `label`), colored from a palette by its
 *     config order — so heterogeneous results stay self-identifying with no
 *     configuration. Skeletons while loading; an empty-state message when there
 *     are none.
 *   - **Global pager** — one {@link PaginationControls} over the cumulative set.
 */

import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "../../../components/ui/alert";
import { Skeleton } from "../../../components/ui/skeleton";
import { ActiveFilters } from "./filters/ActiveFilters";
import { DefaultFilterPanel } from "./filters/DefaultFilterPanel";
import { FilterProvider, FilterResetButton } from "./filters/FilterContext";
import { PaginationControls } from "./controls/PaginationControls";
import { SortControl } from "./controls/SortControl";
import { resolveResultRenderer, type ResultRenderer } from "./results/resolveResultRenderer";
import { MIN_QUERY_LENGTH } from "../constants";
import { ALL_SCOPE, type SearchHandle, type SourceController } from "../types";

export interface MergedSearchResultsProps {
	handle: SearchHandle;
	/**
	 * Per source key: how to render one node in the merged grid. Falls back to
	 * the built-in {@link DefaultResultRow} for any source without an entry.
	 * Pass `false` to skip a source's cards entirely.
	 */
	renderResult?: Record<string, ResultRenderer>;
	/** Message shown when there are no results. Defaults to "No results found." */
	emptyMessage?: string;
	/** Message shown when the query is below {@link MIN_QUERY_LENGTH}. Defaults to "Start your search…" */
	shortQueryMessage?: string;
	/** Number of skeleton placeholders to show while loading. Defaults to `pageSize`. */
	skeletonCount?: number;
	/** Extra classes on the grid container. Defaults to a responsive 1/2/3-column grid. */
	gridClassName?: string;
	/** Extra classes on the outer wrapper. */
	className?: string;
}

const DEFAULT_GRID_CLASS = "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3";

/**
 * Palette for the auto source badges in a mixed grid. A source's color is its
 * index in the config's `sources` array, wrapped around the palette — so badges
 * stay stable and distinct without any per-source configuration. Add more
 * entries here if you routinely mix more source types than there are colors.
 */
const BADGE_PALETTE = [
	"bg-blue-100 text-blue-700",
	"bg-amber-100 text-amber-700",
	"bg-purple-100 text-purple-700",
	"bg-pink-100 text-pink-700",
	"bg-emerald-100 text-emerald-700",
	"bg-sky-100 text-sky-700",
] as const;

export function MergedSearchResults({
	handle,
	renderResult,
	emptyMessage,
	shortQueryMessage = "Start your search…",
	skeletonCount,
	gridClassName = DEFAULT_GRID_CLASS,
	className,
}: MergedSearchResultsProps) {
	const { globalPagination: page, mergedResults, loading, error, q } = handle;
	// Distinguishes "haven't typed enough yet" (useSearch short-circuits below
	// MIN_QUERY_LENGTH without fetching) from a genuine zero-match search — both
	// otherwise present identically as loading=false, mergedResults=[].
	const isShortQuery = q.trim().length < MIN_QUERY_LENGTH;

	// A single source is in scope when the scope is narrowed (selected from the
	// dropdown) or locked (`lockedScope` / restrictTo). Its filter chrome can
	// render meaningfully; under "All" it can't (heterogeneous sources).
	const singleSourceInScope = handle.scope !== ALL_SCOPE;
	const soleController = singleSourceInScope ? handle.inScopeSources[0] : undefined;
	// Per-card source badges only make sense when the grid is genuinely mixed —
	// a single-source grid (narrowed or locked) has one type throughout.
	const showSourceBadges = !singleSourceInScope;
	// Assign each source a stable badge color by its declaration order. Badges
	// only show in "All" scope, where `inScopeSources` is every source in config
	// order, so the index here is the source's config position.
	const badgeColorByKey: Record<string, string> = {};
	handle.inScopeSources.forEach((controller, i) => {
		badgeColorByKey[controller.config.key] = BADGE_PALETTE[i % BADGE_PALETTE.length];
	});

	const skeletons = skeletonCount ?? page.pageSize;

	// Persistent, always-mounted live region: screen readers announce result
	// updates (searching → count → empty → error) without an Enter keypress.
	const liveMessage = loading
		? "Searching…"
		: error
			? "Search failed."
			: isShortQuery
				? shortQueryMessage
				: mergedResults.length === 0
					? (emptyMessage ?? "No results found.")
					: `${page.totalCount} result${page.totalCount === 1 ? "" : "s"}`;

	return (
		<div className={`space-y-6 ${className ?? ""}`}>
			<p className="sr-only" role="status" aria-live="polite">
				{liveMessage}
			</p>

			{soleController && <SingleSourceChrome controller={soleController} />}

			{/* Page-level error — set only when every in-scope source failed (or a
			    whole-request/network failure). Shown once, above the grid. */}
			{error && (
				<Alert variant="destructive" role="alert">
					<AlertCircle />
					<AlertTitle>Search failed</AlertTitle>
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			)}

			{/* Per-source errors — a source that failed while a sibling succeeded
			    surfaces its own banner without blanking the shared grid. Suppressed
			    when the page-level error already covers the all-failed case. */}
			{!error &&
				handle.inScopeSources
					.filter((c) => !!c.error)
					.map((c) => (
						<Alert key={c.config.key} variant="destructive" role="alert">
							<AlertCircle />
							<AlertTitle>Failed to load {c.config.label}</AlertTitle>
							<AlertDescription>{c.error}</AlertDescription>
						</Alert>
					))}

			{/* Results count — its own row, directly above the grid, in every scope.
			    Hidden when there are none (the empty state covers that case). */}
			{!loading && !error && page.totalCount > 0 && (
				<p className="text-sm text-muted-foreground">
					{page.totalCount} result{page.totalCount === 1 ? "" : "s"}
				</p>
			)}

			{loading ? (
				<div className={gridClassName}>
					{Array.from({ length: Math.min(skeletons, 6) }, (_, i) => (
						<Skeleton key={i} className="h-48 w-full rounded-lg" />
					))}
				</div>
			) : isShortQuery ? (
				<p className="py-12 text-center text-sm text-muted-foreground">{shortQueryMessage}</p>
			) : mergedResults.length === 0 ? (
				<p className="py-12 text-center text-sm text-muted-foreground">
					{emptyMessage ?? "No results found."}
				</p>
			) : (
				<ul className={gridClassName}>
					{mergedResults.map(({ sourceKey, node }, i) => {
						const source = handle.sources[sourceKey]?.config;
						if (!source) return null;
						// Resolve via the shared helper so CMS nodes render through
						// CmsResultRow (never DefaultResultRow) in the merged grid too;
						// a `renderResult[key]` override — including `false` — still wins.
						const renderer = resolveResultRenderer(source, renderResult);
						if (renderer === false) return null;
						const rendered = renderer(node);
						const badge =
							showSourceBadges && source ? (
								<SourceBadge
									label={source.labelSingular ?? source.label}
									colorClass={badgeColorByKey[sourceKey]}
								/>
							) : null;
						return (
							<li
								key={getItemKey(sourceKey, node, i)}
								className="flex flex-col gap-1.5 [&>:last-child]:min-h-0 [&>:last-child]:flex-1"
							>
								{badge}
								{rendered}
							</li>
						);
					})}
				</ul>
			)}

			{page.totalCount > 0 && (
				<PaginationControls
					pageIndex={page.pageIndex}
					pageCount={page.pageCount}
					hasNextPage={page.hasNextPage}
					hasPreviousPage={page.hasPreviousPage}
					pageSize={page.pageSize}
					pageSizeOptions={page.pageSizeOptions}
					onNextPage={page.goToNextPage}
					onPreviousPage={page.goToPreviousPage}
					onGoToPage={page.goToPage}
					onPageSizeChange={page.setPageSize}
					disabled={loading || !!error}
				/>
			)}
		</div>
	);
}

function getItemKey(sourceKey: string, node: unknown, fallback: number): string {
	const id = node && typeof node === "object" ? (node as { Id?: unknown }).Id : undefined;
	return typeof id === "string" ? `${sourceKey}:${id}` : `${sourceKey}:${fallback}`;
}

interface SourceBadgeProps {
	label: string;
	colorClass: string;
}

/**
 * Auto source badge shown above each card in a mixed grid — the source's
 * `labelSingular` (falling back to `label`), colored from {@link BADGE_PALETTE}
 * by its config order. Identifies which object type a heterogeneous card came
 * from with no per-app config.
 */
function SourceBadge({ label, colorClass }: SourceBadgeProps) {
	return (
		<span className={`w-fit rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClass}`}>
			{label}
		</span>
	);
}

interface SingleSourceChromeProps {
	controller: SourceController;
}

/**
 * Filter panel + sort + active-filter chips for the one source in scope. Shown
 * whenever the search is narrowed to a single object (selected or locked).
 * Hidden under "All", where heterogeneous per-source filters can't be combined.
 */
function SingleSourceChrome({ controller }: SingleSourceChromeProps) {
	const { config: source, filters, sort } = controller;
	// Filter/sort chrome is SObject-only — narrow on `kind` so the union widening
	// doesn't regress SObject behavior. CMS sources render no filter/sort chrome.
	const sObjectSource = source.kind === "sobject" ? source : null;
	const sortBy = sObjectSource?.sortBy;
	const showFilterPanel = (sObjectSource?.filterBy?.length ?? 0) > 0;
	const showSortControl = (sortBy?.length ?? 0) > 0;
	const showActiveChips = filters.active.length > 0;

	if (!showFilterPanel && !showSortControl && !showActiveChips) return null;

	return (
		<div className="flex flex-col gap-4">
			{showFilterPanel && sObjectSource && (
				<FilterProvider
					filters={filters.active}
					onFilterChange={filters.set}
					onFilterRemove={filters.remove}
					onReset={() => filters.active.forEach((f) => filters.remove(f.field))}
				>
					<div className="rounded-md border p-3 space-y-3">
						<div className="flex items-center justify-between">
							<h2 className="text-sm font-semibold">Filters</h2>
							<FilterResetButton size="sm" />
						</div>
						<div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
							<DefaultFilterPanel source={sObjectSource} />
						</div>
					</div>
				</FilterProvider>
			)}

			{(showSortControl || showActiveChips) && (
				<div className="flex flex-wrap items-center gap-2">
					{showSortControl && sortBy && (
						<SortControl configs={sortBy} sort={sort.current} onSortChange={sort.set} />
					)}
					{showActiveChips && <ActiveFilters filters={filters.active} onRemove={filters.remove} />}
				</div>
			)}
		</div>
	);
}
