/**
 * Drop-in search component. Given a `SearchConfig`, renders a complete
 * search experience: search bar, an aggregate result count, and results.
 *
 * The results layout follows the config's pagination mode — no separate prop:
 *   - `pagination.mode: "per-source"` (default): one stacked section per
 *     source, each with its own filters, sort, and pagination.
 *   - `pagination.mode: "merged"`: a single combined grid across every in-scope
 *     source, driven by one global pager over the cumulative result set (with a
 *     results count and, under a single scope, that source's filter chrome).
 *
 * The simplest possible integration:
 *
 * ```tsx
 * import { Search, config } from ".../features/search";
 * export default function MySearchPage() {
 *   return <Search config={config} />;
 * }
 * ```
 *
 * Override slots:
 *   - `renderResult[sourceKey]` — replace the default row renderer for one
 *     source. Pass `false` to hide that source entirely.
 *   - `renderFilters[sourceKey]` — replace the default filter sidebar for
 *     one source. Pass `false` to suppress filters for that source.
 *   - `renderHeader` — replace the default header (title + subtitle).
 *   - `searchPlaceholder` — placeholder text for the search input.
 *   - `title`, `subtitle` — defaults passed to the built-in header.
 */

import { useMemo, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "../../../components/ui/alert";
import { useSearch } from "../hooks/useSearch";
import { SearchBar } from "./controls/SearchBar";
import { ScopeSelector } from "./controls/ScopeSelector";
import { SearchResults } from "./SearchResults";
import { MergedSearchResults } from "./MergedSearchResults";
import { ALL_SCOPE } from "../types";
import type { SearchConfig, SearchHandle, SObjectSourceConfig } from "../types";

type ResultRenderer = ((node: unknown) => ReactNode) | false;
type FilterRenderer = (() => ReactNode) | false;

/**
 * Locks the search to a single source. Reuses the same shared `config.json`
 * but shows only results matching the given (kind, key) tuple.
 *
 * When set:
 *   - The scope dropdown is hidden.
 *   - URL `?scope=` is not written (the page route already implies the source).
 *   - Only the matching source is fetched and rendered.
 */
export interface RestrictTo {
	kind: SObjectSourceConfig["kind"];
	key: string;
}

interface SearchProps {
	config: SearchConfig;
	renderResult?: Record<string, ResultRenderer>;
	renderFilters?: Record<string, FilterRenderer>;
	emptyMessages?: Record<string, string>;
	searchPlaceholder?: string;
	title?: string;
	subtitle?: string;
	/**
	 * Lock the search to a single source by `(kind, key)`. Hides the scope
	 * dropdown and forces results to that one source. Useful for embedding
	 * a single-object search inside a page where the source is implicit.
	 */
	restrictTo?: RestrictTo;
	/**
	 * Show the source-scope dropdown next to the search bar.
	 * Defaults to `true` when the config has 2+ sources, `false` otherwise
	 * (a one-source dropdown would be redundant). Always hidden when
	 * `restrictTo` is set.
	 */
	showScopeSelector?: boolean;
	/** Label for the "search everything" entry in the scope dropdown. */
	allScopeLabel?: string;
	/** Optional override for the entire header region. */
	renderHeader?: (handle: SearchHandle) => ReactNode;
	className?: string;
}

export function Search({
	config,
	renderResult,
	renderFilters,
	emptyMessages,
	searchPlaceholder = "Search…",
	title = "Search",
	subtitle,
	restrictTo,
	showScopeSelector,
	allScopeLabel,
	renderHeader,
	className,
}: SearchProps) {
	// Resolve restrictTo to a lockedScope value, surfacing a clear error if
	// the (kind, key) pair doesn't match any source. Memoize so it's
	// stable across renders.
	const lockedScope = useMemo<string | undefined>(() => {
		if (!restrictTo) return undefined;
		const match = config.sources.find(
			(s) => s.kind === restrictTo.kind && s.key === restrictTo.key,
		);
		if (!match) {
			console.warn(
				`<Search restrictTo>: no source with kind="${restrictTo.kind}" and key="${restrictTo.key}" in config. Falling back to "all".`,
			);
			return undefined;
		}
		return match.key;
	}, [restrictTo, config.sources]);

	const handle = useSearch(config, { lockedScope });
	// The results layout follows the pagination mode — a "merged" config means a
	// single combined grid, "per-source" (default) means one section per source.
	// There is no separate `layout` prop: the two would only ever be set in lockstep.
	const merged = config.pagination?.mode === "merged";
	const totalResults = Object.values(handle.sources).reduce(
		(acc, controller) => acc + (controller.result?.totalCount ?? 0),
		0,
	);
	const shouldShowScope = !handle.scopeLocked && (showScopeSelector ?? config.sources.length >= 2);
	// The aggregate count is only meaningful when results from more than one
	// source are combined. With a single configured source, a locked scope, or
	// a specific source picked in the dropdown, exactly one source is on screen
	// and that source's own section already shows its count — so suppress the
	// redundant total here.
	const sourcesInScope = handle.scope === ALL_SCOPE ? config.sources.length : 1;
	// In merged mode the results grid renders its own count row directly above the
	// grid (in every scope), so the inline aggregate here would be redundant.
	const showTotalResults = !merged && sourcesInScope >= 2;

	return (
		<div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 ${className ?? ""}`}>
			{renderHeader ? (
				renderHeader(handle)
			) : (
				<header className="space-y-2">
					<h1 className="text-2xl font-bold">{title}</h1>
					{subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
				</header>
			)}

			<div className="flex flex-wrap items-center gap-3">
				<SearchBar value={handle.q} onChange={handle.setQ} placeholder={searchPlaceholder} />
				{shouldShowScope && (
					<ScopeSelector
						config={config}
						scope={handle.scope}
						onScopeChange={handle.setScope}
						allLabel={allScopeLabel}
						discoveredContentTypes={handle.discoveredContentTypes}
					/>
				)}
			</div>

			{merged ? (
				<MergedSearchResults
					handle={handle}
					renderResult={renderResult}
					emptyMessage={emptyMessages?.[handle.scope]}
				/>
			) : (
				<>
					{handle.error ? (
						/* Page-level failure (every queried source failed, or a
						   whole-request/network error). Show the single consolidated
						   banner and nothing else — the per-source sections would each
						   repeat the same "Failed to load <source>" error and their
						   (now empty) filter/sort chrome, so suppress them entirely. */
						<Alert variant="destructive" role="alert">
							<AlertCircle aria-hidden="true" />
							<AlertTitle>Search failed</AlertTitle>
							<AlertDescription>{handle.error}</AlertDescription>
						</Alert>
					) : (
						<>
							{/* Aggregate count on its own row, directly above the results —
							    only in "All" scope, where the per-source sections don't each
							    carry a single meaningful total. */}
							{showTotalResults && !handle.loading && (
								<p className="text-sm text-muted-foreground" role="status">
									{totalResults} total result{totalResults === 1 ? "" : "s"}
								</p>
							)}
							<SearchResults
								handle={handle}
								renderResult={renderResult}
								renderFilters={renderFilters}
								emptyMessages={emptyMessages}
							/>
						</>
					)}
				</>
			)}
		</div>
	);
}
