/**
 * useSearch — orchestrates configuration-driven multi-source search.
 *
 * Owns:
 *  - global `q` (one search box drives all sources)
 *  - per-source filters / sort / pagination (independent state per source)
 *  - URL sync (debounced; namespace `s.<key>.f.<field>=...`)
 *  - one batched GraphQL fetch on every state change
 *
 * Returns a per-source `controller` map plus aggregate loading/error flags.
 * Rendering and routing are the caller's responsibility.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { runSearch } from "../api/searchService";
import {
	GLOBAL_QUERY_KEY,
	readSourceParams,
	writeSourceParams,
	type ActiveFilterValue,
} from "../utils/filterUtils";
import type { SortState } from "../utils/sortUtils";
import { debounce } from "../utils/debounce";
import type {
	SObjectSourceConfig,
	SourceController,
	SourceResult,
	SearchConfig,
	SearchHandle,
	SearchScope,
	GlobalPagination,
	MergedResultItem,
} from "../types";
import { ALL_SCOPE } from "../types";

const URL_SYNC_DEBOUNCE_MS = 300;
const SCOPE_KEY = "scope";

/**
 * Returns true when `source` should participate in the current scope —
 * either the scope is "all" or the scope matches this source's key.
 */
function isSourceInScope(scope: SearchScope, sourceKey: string): boolean {
	return scope === ALL_SCOPE || scope === sourceKey;
}

interface SourceLocalState {
	filters: ActiveFilterValue[];
	sort: SortState | null;
	pageSize: number;
	pageIndex: number;
	afterCursor: string | undefined;
	cursorStack: string[];
}

/** Defaults applied when `config.pagination` is omitted. */
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_PAGE_SIZE_OPTIONS = [10, 25, 50];

interface ResolvedPagination {
	mode: "per-source" | "merged";
	mergeOrder: "sequential" | "interleaved" | "proportional";
	pageSize: number;
	pageSizeOptions: number[];
}

/** Resolves the single global pagination config, filling in defaults. */
function resolvePagination(config: SearchConfig): ResolvedPagination {
	const p = config.pagination;
	const pageSizeOptions =
		p?.pageSizeOptions && p.pageSizeOptions.length > 0
			? p.pageSizeOptions
			: DEFAULT_PAGE_SIZE_OPTIONS;
	return {
		mode: p?.mode ?? "per-source",
		mergeOrder: p?.mergeOrder ?? "sequential",
		pageSize: p?.pageSize ?? pageSizeOptions[0] ?? DEFAULT_PAGE_SIZE,
		pageSizeOptions,
	};
}

/** Clamps a requested size to the configured options. */
function validatePageSize(pagination: ResolvedPagination, size: number): number {
	const valid = pagination.pageSizeOptions;
	if (valid.length === 0) return size;
	return valid.includes(size) ? size : pagination.pageSize;
}

function initSourceState(
	source: SObjectSourceConfig,
	params: URLSearchParams,
	pagination: ResolvedPagination,
): SourceLocalState {
	const read = readSourceParams(params, source.key, source.filterBy ?? []);
	const sort = read.sort ?? source.defaultSort ?? null;
	const pageSize = validatePageSize(pagination, read.pageSize ?? pagination.pageSize);
	return {
		filters: read.filters,
		sort,
		pageSize,
		pageIndex: read.pageIndex,
		afterCursor: undefined,
		cursorStack: [],
	};
}

export interface UseSearchOptions {
	/**
	 * Lock the search to a single source key (or "all"). When set:
	 *   - `scope` is forced to this value and `setScope` becomes a no-op.
	 *   - The URL never writes `?scope=` (it's implicit in the page route).
	 *   - The dropdown should be hidden by the caller.
	 *
	 * Use when you embed the search inside a page that already represents
	 * the source (e.g. `/accounts/search` rendering only Accounts).
	 */
	lockedScope?: SearchScope;
}

export function useSearch(config: SearchConfig, options?: UseSearchOptions): SearchHandle {
	const [searchParams, setSearchParams] = useSearchParams();
	const lockedScope = options?.lockedScope;

	// Single global pagination config — page size, options, mode, merge order.
	// There is no per-source pagination; this applies to every scope, including
	// locked single-object pages and dropdown-narrowed scope.
	const pagination = useMemo(
		() => resolvePagination(config),
		// config is stable for the hook's lifetime.
		// eslint-disable-next-line react-hooks/exhaustive-deps
		[],
	);

	// One-time seed from URL.
	const initialSourceStates = useMemo(() => {
		const map: Record<string, SourceLocalState> = {};
		for (const source of config.sources) {
			map[source.key] = initSourceState(source, searchParams, pagination);
		}
		return map;
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);
	const initialQ = useMemo(() => searchParams.get(GLOBAL_QUERY_KEY) ?? "", []);
	const initialScope = useMemo<SearchScope>(() => {
		// When the caller locks the scope, that always wins over the URL.
		if (lockedScope !== undefined) {
			if (lockedScope === ALL_SCOPE) return ALL_SCOPE;
			return config.sources.some((s) => s.key === lockedScope) ? lockedScope : ALL_SCOPE;
		}
		const raw = searchParams.get(SCOPE_KEY);
		if (!raw || raw === ALL_SCOPE) return ALL_SCOPE;
		return config.sources.some((s) => s.key === raw) ? raw : ALL_SCOPE;
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const [q, setQState] = useState(initialQ);
	const [scope, setScopeState] = useState<SearchScope>(initialScope);
	const [sourceStates, setSourceStates] =
		useState<Record<string, SourceLocalState>>(initialSourceStates);

	// Merged pagination treats the cumulative result set as one fixed-size-paged
	// list (see SearchPaginationConfig). It needs a single global page index +
	// size rather than the per-source cursors above; per-source state is still
	// kept (for filters / sort) but its cursors stay at page 0.
	const mergedMode = pagination.mode === "merged";
	const mergeOrder = pagination.mergeOrder;

	const [globalPageIndex, setGlobalPageIndex] = useState(0);
	const [globalPageSize, setGlobalPageSize] = useState(pagination.pageSize);

	// Snapshot ref so debounced URL sync sees the latest state without
	// recreating callbacks on every render.
	const stateRef = useRef({ q, scope, sourceStates });
	useEffect(() => {
		stateRef.current = { q, scope, sourceStates };
	});

	// -- URL sync --------------------------------------------------------------

	const syncToUrl = useCallback(
		(nextQ: string, nextScope: SearchScope, nextStates: Record<string, SourceLocalState>) => {
			const params = new URLSearchParams();
			if (nextQ) params.set(GLOBAL_QUERY_KEY, nextQ);
			// Skip writing ?scope when caller has locked the scope — it's
			// already implicit in the page route.
			if (lockedScope === undefined && nextScope !== ALL_SCOPE) {
				params.set(SCOPE_KEY, nextScope);
			}
			for (const source of config.sources) {
				const state = nextStates[source.key];
				if (!state) continue;
				writeSourceParams(
					params,
					source.key,
					state.filters,
					state.sort,
					state.pageSize,
					state.pageIndex,
					// Omit sort / page size from the URL when they equal the
					// defaults, so a reset (or untouched source) leaves a clean
					// query string instead of echoing the defaults.
					{ sort: source.defaultSort ?? null, pageSize: pagination.pageSize },
				);
			}
			setSearchParams(params, { replace: true });
		},
		[config.sources, setSearchParams, lockedScope, pagination.pageSize],
	);

	const debouncedSyncRef = useRef(debounce(syncToUrl, URL_SYNC_DEBOUNCE_MS));
	useEffect(() => {
		debouncedSyncRef.current = debounce(syncToUrl, URL_SYNC_DEBOUNCE_MS);
	}, [syncToUrl]);

	// Update one source's state and (optionally) reset its pagination.
	const updateSource = useCallback(
		(
			sourceKey: string,
			updater: (prev: SourceLocalState) => SourceLocalState,
			resetPagination: boolean,
		) => {
			// A filter / sort / page-size change reshapes the result set, so the
			// global merged page returns to the first page too.
			if (resetPagination) setGlobalPageIndex(0);
			setSourceStates((prev) => {
				const prior = prev[sourceKey];
				if (!prior) return prev;
				let next = updater(prior);
				if (resetPagination) {
					next = { ...next, pageIndex: 0, afterCursor: undefined, cursorStack: [] };
				}
				const merged = { ...prev, [sourceKey]: next };
				debouncedSyncRef.current(stateRef.current.q, stateRef.current.scope, merged);
				return merged;
			});
		},
		[],
	);

	// -- Global q --------------------------------------------------------------

	const setQ = useCallback((nextQ: string) => {
		setQState(nextQ);
		// A new term changes the whole result set — back to the first page.
		setGlobalPageIndex(0);
		// Changing the global term invalidates every cursor.
		setSourceStates((prev) => {
			const next: Record<string, SourceLocalState> = {};
			for (const [key, state] of Object.entries(prev)) {
				next[key] = { ...state, pageIndex: 0, afterCursor: undefined, cursorStack: [] };
			}
			debouncedSyncRef.current(nextQ, stateRef.current.scope, next);
			return next;
		});
	}, []);

	// -- Scope -----------------------------------------------------------------

	const setScope = useCallback(
		(nextScope: SearchScope) => {
			// Locked scope wins over user input — silently no-op.
			if (lockedScope !== undefined) return;
			// Reject unknown scope values; fall back to "all".
			const validated: SearchScope =
				nextScope === ALL_SCOPE || config.sources.some((s) => s.key === nextScope)
					? nextScope
					: ALL_SCOPE;
			setScopeState(validated);
			// The visible set changes — reset the global page too.
			setGlobalPageIndex(0);
			// Narrowing or widening invalidates every cursor — the visible result
			// set is changing.
			setSourceStates((prev) => {
				const next: Record<string, SourceLocalState> = {};
				for (const [key, state] of Object.entries(prev)) {
					next[key] = { ...state, pageIndex: 0, afterCursor: undefined, cursorStack: [] };
				}
				debouncedSyncRef.current(stateRef.current.q, validated, next);
				return next;
			});
		},
		[config.sources, lockedScope],
	);

	// -- Reset all -------------------------------------------------------------

	const resetAll = useCallback(() => {
		setQState("");
		setGlobalPageIndex(0);
		// Preserve locked scope; otherwise widen back to "all".
		const nextScope: SearchScope = lockedScope ?? ALL_SCOPE;
		setScopeState(nextScope);
		const empty: Record<string, SourceLocalState> = {};
		for (const source of config.sources) {
			empty[source.key] = {
				filters: [],
				sort: source.defaultSort ?? null,
				pageSize: pagination.pageSize,
				pageIndex: 0,
				afterCursor: undefined,
				cursorStack: [],
			};
		}
		setSourceStates(empty);
		setGlobalPageSize(pagination.pageSize);
		syncToUrl("", nextScope, empty);
	}, [config.sources, syncToUrl, lockedScope, pagination.pageSize]);

	// -- Fetch -----------------------------------------------------------------

	const requestKey = useMemo(() => {
		// Stable string key that changes only when something fetch-relevant changes.
		// Sources outside the current scope are listed (with `skip: true`) so
		// the key still changes when scope toggles, but they don't contribute
		// per-source state to the diff.
		return JSON.stringify({
			q,
			scope,
			// Merged mode paginates globally: every in-scope source fetches the
			// same front-anchored window, so the global page/size drive the fetch
			// rather than per-source cursors.
			m: mergedMode ? { gp: globalPageIndex, gs: globalPageSize } : null,
			s: config.sources.map((source) => {
				if (!isSourceInScope(scope, source.key)) {
					return { k: source.key, skip: true };
				}
				const st = sourceStates[source.key];
				return {
					k: source.key,
					f: st?.filters,
					o: st?.sort,
					// In merged mode per-source size/cursor are overridden below.
					p: mergedMode ? undefined : st?.pageSize,
					a: mergedMode ? undefined : (st?.afterCursor ?? null),
				};
			}),
		});
	}, [q, scope, sourceStates, config.sources, mergedMode, globalPageIndex, globalPageSize]);

	const [results, setResults] = useState<Record<string, SourceResult>>({});
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const fetchGenRef = useRef(0);

	useEffect(() => {
		const generation = ++fetchGenRef.current;
		setLoading(true);
		setError(null);

		const activeSources = config.sources.filter((source) => isSourceInScope(scope, source.key));

		// All sources gated out — clear results and exit without firing a request.
		if (activeSources.length === 0) {
			setResults({});
			setLoading(false);
			return;
		}

		// Merged mode: fetch the whole front-anchored window — (page + 1) * size
		// rows — from every in-scope source, with no cursor. Concatenating these
		// and slicing [page*size, (page+1)*size) yields the exact global page,
		// because the first (page+1)*size items of the concatenation are always
		// the true merged prefix regardless of how rows interleave.
		const mergedFetchSize = (globalPageIndex + 1) * globalPageSize;

		const requests = activeSources.map((source) => {
			const st = sourceStates[source.key]!;
			return {
				source,
				q,
				filters: st.filters,
				sort: st.sort,
				pageSize: mergedMode ? mergedFetchSize : st.pageSize,
				afterCursor: mergedMode ? undefined : st.afterCursor,
			};
		});

		runSearch(requests)
			.then((resp) => {
				if (generation !== fetchGenRef.current) return;
				setResults(resp);
			})
			.catch((err: unknown) => {
				if (generation !== fetchGenRef.current) return;
				console.error(err);
				setError(err instanceof Error ? err.message : "Unified search failed");
			})
			.finally(() => {
				if (generation !== fetchGenRef.current) return;
				setLoading(false);
			});
		// requestKey is the dependency-of-record; sourceStates and q are
		// captured via the ref-like closure above each render.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [requestKey]);

	// -- Per-source controllers ------------------------------------------------

	const controllers = useMemo(() => {
		const out: Record<string, SourceController> = {};
		for (const source of config.sources) {
			const state = sourceStates[source.key];
			const result = results[source.key] ?? null;

			const setFilter = (field: string, value: ActiveFilterValue | undefined) => {
				updateSource(
					source.key,
					(prev) => {
						const filtered = prev.filters.filter((f) => f.field !== field);
						if (value) filtered.push(value);
						return { ...prev, filters: filtered };
					},
					true,
				);
			};
			const removeFilter = (field: string) => {
				updateSource(
					source.key,
					(prev) => ({
						...prev,
						filters: prev.filters.filter((f) => f.field !== field),
					}),
					true,
				);
			};
			const setSort = (sort: SortState | null) => {
				updateSource(source.key, (prev) => ({ ...prev, sort }), true);
			};
			const setPageSize = (size: number) => {
				updateSource(
					source.key,
					(prev) => ({ ...prev, pageSize: validatePageSize(pagination, size) }),
					true,
				);
			};
			const goToNextPage = () => {
				const cursor = result?.pageInfo?.endCursor;
				if (!cursor) return;
				updateSource(
					source.key,
					(prev) => ({
						...prev,
						cursorStack: [...prev.cursorStack, cursor],
						afterCursor: cursor,
						pageIndex: prev.pageIndex + 1,
					}),
					false,
				);
			};
			const goToPreviousPage = () => {
				updateSource(
					source.key,
					(prev) => {
						if (prev.pageIndex === 0) return prev;
						const nextStack = prev.cursorStack.slice(0, -1);
						return {
							...prev,
							cursorStack: nextStack,
							afterCursor: nextStack[nextStack.length - 1],
							pageIndex: Math.max(0, prev.pageIndex - 1),
						};
					},
					false,
				);
			};

			out[source.key] = {
				config: source,
				result,
				loading,
				error,
				filters: {
					active: state?.filters ?? [],
					set: setFilter,
					remove: removeFilter,
				},
				sort: {
					current: state?.sort ?? null,
					set: setSort,
				},
				pagination: {
					pageSize: state?.pageSize ?? pagination.pageSize,
					pageSizeOptions: pagination.pageSizeOptions,
					pageIndex: state?.pageIndex ?? 0,
					hasNextPage: result?.pageInfo?.hasNextPage ?? false,
					hasPreviousPage: (state?.pageIndex ?? 0) > 0,
					setPageSize,
					goToNextPage,
					goToPreviousPage,
				},
			};
		}
		return out;
	}, [config.sources, sourceStates, results, loading, error, updateSource, pagination]);

	const scopeLocked = lockedScope !== undefined;

	// -- Aggregate (cross-source) view -----------------------------------------

	const inScopeSources = useMemo(
		() =>
			config.sources
				.map((s) => controllers[s.key])
				.filter((c): c is SourceController => !!c && isSourceInScope(scope, c.config.key)),
		[config.sources, controllers, scope],
	);

	// Cumulative result count is mode-independent: sum the in-scope totals.
	const totalCount = useMemo(
		() =>
			inScopeSources.reduce(
				(sum, c) => sum + (c.result?.totalCount ?? c.result?.nodes.length ?? 0),
				0,
			),
		[inScopeSources],
	);

	// Every in-scope source's fetched nodes flattened into one list, ordered per
	// `mergeOrder`:
	//   - sequential: all of source 1, then source 2, … (config order).
	//   - interleaved: round-robin, one node per source per round — equal priority.
	//   - proportional: each item gets a key (i + 0.5) / weight (weight = source's
	//     totalCount); sorting by key spreads each source evenly across the list
	//     in proportion to its size, so larger sources appear more often.
	// All three stay exact in merged mode. Each source fetched (page + 1) * size
	// rows from its front, so the first (page + 1) * size items of this list are
	// the true cumulative prefix: the round index / sort position of any item in
	// that prefix needs at most that many rows from a single source, and those
	// rows were all fetched, so per-source truncation never disturbs the slice.
	// Proportional uses the true totalCount as the weight (not the fetched
	// length), keeping each item's key — and thus the order — stable across pages.
	const concatenatedNodes = useMemo<MergedResultItem[]>(() => {
		const lists = inScopeSources.map((c) => ({
			key: c.config.key,
			nodes: c.result?.nodes ?? [],
			// Proportional weight: the source's true total, falling back to how many
			// we actually have when totalCount is absent.
			weight: c.result?.totalCount ?? c.result?.nodes.length ?? 0,
		}));
		const out: MergedResultItem[] = [];

		if (mergeOrder === "interleaved") {
			const maxLen = lists.reduce((m, l) => Math.max(m, l.nodes.length), 0);
			for (let round = 0; round < maxLen; round++) {
				for (const l of lists) {
					if (round < l.nodes.length) out.push({ sourceKey: l.key, node: l.nodes[round] });
				}
			}
		} else if (mergeOrder === "proportional") {
			// Tag each node with its spread key + source index, then stable-sort.
			const tagged = lists.flatMap((l, sIdx) =>
				l.nodes.map((node, i) => ({
					sourceKey: l.key,
					node,
					sIdx,
					i,
					sortKey: (i + 0.5) / (l.weight > 0 ? l.weight : 1),
				})),
			);
			tagged.sort((a, b) => a.sortKey - b.sortKey || a.sIdx - b.sIdx || a.i - b.i);
			for (const t of tagged) out.push({ sourceKey: t.sourceKey, node: t.node });
		} else {
			for (const l of lists) {
				for (const node of l.nodes) out.push({ sourceKey: l.key, node });
			}
		}
		return out;
	}, [inScopeSources, mergeOrder]);

	// -- Merged mode: one fixed-size-paged list over the cumulative results -----

	const mergedGlobalPagination = useMemo<GlobalPagination>(() => {
		// Options come from the global pagination config, NOT the in-scope source —
		// so narrowing the dropdown to one object keeps the global page sizes.
		const pageSizeOptions = pagination.pageSizeOptions;
		const pageCount = totalCount === 0 ? 0 : Math.ceil(totalCount / globalPageSize);
		// Clamp in case totalCount shrank (e.g. a filter) below the current page.
		const pageIndex = pageCount === 0 ? 0 : Math.min(globalPageIndex, pageCount - 1);
		return {
			pageIndex,
			pageCount,
			pageSize: globalPageSize,
			pageSizeOptions,
			hasNextPage: pageIndex + 1 < pageCount,
			hasPreviousPage: pageIndex > 0,
			totalCount,
			goToNextPage: () => setGlobalPageIndex((p) => p + 1),
			goToPreviousPage: () => setGlobalPageIndex((p) => Math.max(0, p - 1)),
			goToPage: (next: number) => setGlobalPageIndex(Math.max(0, Math.floor(next))),
			setPageSize: (size: number) => {
				setGlobalPageSize(size);
				setGlobalPageIndex(0);
			},
		};
	}, [pagination, totalCount, globalPageSize, globalPageIndex]);

	const mergedModeResults = useMemo<MergedResultItem[]>(() => {
		const start = mergedGlobalPagination.pageIndex * globalPageSize;
		return concatenatedNodes.slice(start, start + globalPageSize);
	}, [concatenatedNodes, mergedGlobalPagination.pageIndex, globalPageSize]);

	// -- Per-source mode: independent cursors, "global page" = furthest source --
	//
	// Sources paginate with independent cursors (there is no global offset), so a
	// "global page" is the furthest-advanced in-scope source's page. A source
	// that runs out of pages is left behind at a lower pageIndex and stops
	// contributing nodes — its last page was already shown on an earlier global
	// page, so re-emitting it would duplicate rows in the merged list.

	const perSourceGlobalPagination = useMemo<GlobalPagination>(() => {
		const lead = inScopeSources[0];
		const pageSize = lead?.pagination.pageSize ?? pagination.pageSize;
		const pageSizeOptions = pagination.pageSizeOptions;

		const pageIndex = inScopeSources.reduce((max, c) => Math.max(max, c.pagination.pageIndex), 0);

		// Pages a source spans: prefer totalCount; otherwise a lower bound from its
		// own position (current page, plus one more if it reports a next page).
		const pageCount = inScopeSources.reduce((max, c) => {
			const tc = c.result?.totalCount;
			const span =
				tc != null && pageSize > 0
					? Math.max(1, Math.ceil(tc / pageSize))
					: c.pagination.pageIndex + (c.pagination.hasNextPage ? 2 : 1);
			return Math.max(max, span);
		}, 0);

		const hasNextPage = inScopeSources.some((c) => c.pagination.hasNextPage);
		const hasPreviousPage = pageIndex > 0;

		const goToNextPage = () =>
			inScopeSources.forEach((c) => {
				if (c.pagination.hasNextPage) c.pagination.goToNextPage();
			});
		const goToPreviousPage = () =>
			inScopeSources.forEach((c) => {
				if (c.pagination.pageIndex === pageIndex) c.pagination.goToPreviousPage();
			});

		return {
			pageIndex,
			pageCount: totalCount === 0 ? 0 : pageCount,
			pageSize,
			pageSizeOptions,
			hasNextPage,
			hasPreviousPage,
			totalCount,
			goToNextPage,
			goToPreviousPage,
			// Cursors can't seek to an arbitrary offset — honour adjacent pages only.
			goToPage: (next: number) => {
				if (next === pageIndex + 1 && hasNextPage) goToNextPage();
				else if (next === pageIndex - 1 && hasPreviousPage) goToPreviousPage();
			},
			setPageSize: (size: number) => inScopeSources.forEach((c) => c.pagination.setPageSize(size)),
		};
	}, [inScopeSources, totalCount, pagination]);

	const perSourceResults = useMemo<MergedResultItem[]>(() => {
		const globalPageIndex = perSourceGlobalPagination.pageIndex;
		return concatenatedNodes.filter((item) => {
			const c = controllers[item.sourceKey];
			// Only sources caught up to the current global page contribute; a
			// left-behind source already showed its final page earlier.
			return c?.pagination.pageIndex === globalPageIndex;
		});
	}, [concatenatedNodes, controllers, perSourceGlobalPagination.pageIndex]);

	const globalPagination = mergedMode ? mergedGlobalPagination : perSourceGlobalPagination;
	const mergedResults = mergedMode ? mergedModeResults : perSourceResults;

	return useMemo(
		() => ({
			q,
			setQ,
			scope,
			setScope,
			scopeLocked,
			sources: controllers,
			inScopeSources,
			mergedResults,
			globalPagination,
			loading,
			error,
			resetAll,
		}),
		[
			q,
			setQ,
			scope,
			setScope,
			scopeLocked,
			controllers,
			inScopeSources,
			mergedResults,
			globalPagination,
			loading,
			error,
			resetAll,
		],
	);
}
