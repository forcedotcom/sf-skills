/**
 * Renders one source's slice of a search result: optional filter
 * panel, sort dropdown, active-filter chips, the result list (delegated to
 * the caller via `renderResult`), and pagination controls.
 *
 * The component is "smart" only about orchestration. The actual list-item UI
 * is owned by the application via the `renderResult(node)` callback —
 * search never decides how an Account or Contact card looks.
 */

import type { ReactNode } from "react";
import { AlertCircle, SearchX } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "../../../components/ui/alert";
import { Skeleton } from "../../../components/ui/skeleton";
import { ActiveFilters } from "./filters/ActiveFilters";
import { FilterProvider, FilterResetButton } from "./filters/FilterContext";
import { PaginationControls } from "./controls/PaginationControls";
import { SortControl } from "./controls/SortControl";
import type { SourceController } from "../types";

interface SourceSectionProps {
	controller: SourceController;
	renderResult: (node: unknown) => ReactNode;
	/** Optional filter UI (TextFilter, SelectFilter, ...) rendered above the results. */
	renderFilters?: () => ReactNode;
	/**
	 * Suppress the filter panel, the active-filter chips, and the sort
	 * dropdown. Pre-existing filter / sort selections stay in state (and
	 * apply to the GraphQL query) so the caller can restore the chrome
	 * without losing the user's selections, but no chrome surface is rendered.
	 *
	 * Set by `<SearchResults>` when the current scope is "all" — per-source
	 * controls would be unreachable while every source is on screen, and
	 * dangling chips would be confusing.
	 */
	hideFilterChrome?: boolean;
	emptyMessage?: string;
	className?: string;
}

export function SourceSection({
	controller,
	renderResult,
	renderFilters,
	hideFilterChrome,
	emptyMessage,
	className,
}: SourceSectionProps) {
	const { config, result, loading, error, filters, sort, pagination } = controller;
	const nodes = result?.nodes ?? [];
	const totalCount = result?.totalCount;
	const showResults = !loading && !error && nodes.length > 0;
	const showEmpty = !loading && !error && nodes.length === 0;

	const pageSizeOptions = pagination.pageSizeOptions ?? [pagination.pageSize];

	// `sortBy` / `idField` are SObject-only — narrow on `kind` so the union
	// widening of `config` doesn't regress SObject behavior (CMS has neither).
	const sortBy = config.kind === "sobject" ? config.sortBy : undefined;
	const idField = config.kind === "sobject" ? config.idField : undefined;

	const showFilterPanel = !!renderFilters && !hideFilterChrome;
	const showActiveChips = !hideFilterChrome && filters.active.length > 0;
	const showSortControl = !hideFilterChrome && (sortBy?.length ?? 0) > 0;

	// Persistent, always-mounted live region: screen readers announce result
	// updates (searching → count → empty → error) without an Enter keypress.
	const liveMessage = loading
		? "Searching…"
		: error
			? `Failed to load ${config.label}.`
			: showEmpty
				? (emptyMessage ?? `No ${config.label.toLowerCase()} found.`)
				: totalCount != null
					? `${config.label}: ${totalCount} ${totalCount === 1 ? "result" : "results"}`
					: "";

	return (
		<section className={`flex flex-col gap-6 ${className ?? ""}`}>
			<p className="sr-only" role="status" aria-live="polite">
				{liveMessage}
			</p>

			{showFilterPanel && (
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
							{renderFilters!()}
						</div>
					</div>
				</FilterProvider>
			)}

			<div className="min-w-0">
				<header className="flex flex-wrap items-baseline gap-3 mb-3">
					<h2 className="text-lg font-semibold">{config.label}</h2>
				</header>

				{(showSortControl || showActiveChips) && (
					<div className="flex flex-wrap items-center gap-2 mb-3">
						{showSortControl && sortBy ? (
							<SortControl configs={sortBy} sort={sort.current} onSortChange={sort.set} />
						) : null}
						{showActiveChips && (
							<ActiveFilters filters={filters.active} onRemove={filters.remove} />
						)}
					</div>
				)}

				{/* Result count, shown just above the results in every scope —
				    including a locked / single-source (restrictTo) view. */}
				{!loading && !error && totalCount != null && (
					<p className="text-sm text-muted-foreground mb-3">
						{totalCount} {totalCount === 1 ? "result" : "results"}
					</p>
				)}

				<div className="min-h-32">
					{loading && (
						<div className="space-y-2">
							{Array.from({ length: Math.min(pagination.pageSize, 5) }, (_, i) => (
								<Skeleton key={i} className="h-12 w-full" />
							))}
						</div>
					)}

					{error && (
						<Alert variant="destructive" role="alert">
							<AlertCircle />
							<AlertTitle>Failed to load {config.label}</AlertTitle>
							<AlertDescription>{error}</AlertDescription>
						</Alert>
					)}

					{showResults && (
						<ul className="divide-y">
							{nodes.map((node, i) => (
								<li key={getNodeKey(node, idField, i)} className="py-3">
									{renderResult(node)}
								</li>
							))}
						</ul>
					)}

					{showEmpty && (
						<div className="flex flex-col items-center justify-center py-10 text-center">
							<SearchX className="size-10 text-muted-foreground mb-3" />
							<p className="text-sm text-muted-foreground">
								{emptyMessage ?? `No ${config.label.toLowerCase()} found.`}
							</p>
						</div>
					)}
				</div>

				<PaginationControls
					pageIndex={pagination.pageIndex}
					hasNextPage={pagination.hasNextPage}
					hasPreviousPage={pagination.hasPreviousPage}
					pageSize={pagination.pageSize}
					pageSizeOptions={pageSizeOptions}
					onNextPage={pagination.goToNextPage}
					onPreviousPage={pagination.goToPreviousPage}
					onPageSizeChange={pagination.setPageSize}
					disabled={loading || !!error}
					idPrefix={`page-size-${config.key}`}
				/>
			</div>
		</section>
	);
}

function getNodeKey(node: unknown, idField: string | undefined, fallback: number): string | number {
	if (node && typeof node === "object") {
		const id = (node as Record<string, unknown>)[idField ?? "Id"];
		if (typeof id === "string" || typeof id === "number") return id;
	}
	return fallback;
}
