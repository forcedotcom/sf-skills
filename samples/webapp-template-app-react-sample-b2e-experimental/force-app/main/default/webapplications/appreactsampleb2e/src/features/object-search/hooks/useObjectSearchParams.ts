import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import type { FilterFieldConfig, ActiveFilterValue } from "../utils/filterUtils";
import type { SortFieldConfig, SortState } from "../utils/sortUtils";
import { filtersToSearchParams, searchParamsToFilters, buildFilter } from "../utils/filterUtils";
import { buildOrderBy } from "../utils/sortUtils";
import { debounce } from "../utils/debounce";

/** How long to wait before flushing local state changes to the URL. */
const URL_SYNC_DEBOUNCE_MS = 300;

export interface PaginationConfig {
	defaultPageSize: number;
	validPageSizes: number[];
}

/**
 * Manages filter, sort, and cursor-based pagination state for an object search page.
 *
 * ## State model
 * Local React state is the primary driver for instant UI updates.
 * URL search params act as the durable source of truth so that a page
 * refresh or shared link restores the same view. Changes are synced to
 * the URL via a debounced write (300 ms) to avoid excessive history entries.
 *
 * ## Return shape
 * Returns memoized groups so each group's reference is stable unless its
 * contents change — safe to pass directly as props to `React.memo` children.
 *
 * - `filters`    — active filter values + set/remove callbacks
 * - `sort`       — current sort state + set callback
 * - `query`      — derived `where` / `orderBy` objects ready for the API
 * - `pagination` — page size, page index, cursor, and navigation callbacks
 * - `resetAll`   — clears all filters, sort, and pagination in one call
 */
export function useObjectSearchParams<TFilter, TOrderBy>(
	filterConfigs: FilterFieldConfig[],
	_sortConfigs?: SortFieldConfig[],
	paginationConfig?: PaginationConfig,
) {
	const defaultPageSize = paginationConfig?.defaultPageSize ?? 10;
	const validPageSizes = paginationConfig?.validPageSizes ?? [defaultPageSize];
	const [searchParams, setSearchParams] = useSearchParams();

	// Seed local state from URL on initial load
	const initial = useMemo(
		() => searchParamsToFilters(searchParams, filterConfigs),
		// Only run on mount — local state takes over after that, no deps needed
		// eslint-disable-next-line react-hooks/exhaustive-deps
		[],
	);

	const [filters, setFilters] = useState<ActiveFilterValue[]>(initial.filters);
	const [sort, setLocalSort] = useState<SortState | null>(initial.sort);

	// Pagination — cursor-based with a stack to support "previous page" navigation.
	const getValidPageSize = (size: number) =>
		validPageSizes.includes(size) ? size : defaultPageSize;

	const [pageSize, setPageSizeState] = useState<number>(
		getValidPageSize(initial.pageSize ?? defaultPageSize),
	);
	const [pageIndex, setPageIndex] = useState(initial.pageIndex);
	const [afterCursor, setAfterCursor] = useState<string | undefined>(undefined);
	const cursorStackRef = useRef<string[]>([]);

	// Debounced URL sync — keeps URL in sync without blocking the UI
	const syncToUrl = useCallback(
		(
			nextFilters: ActiveFilterValue[],
			nextSort: SortState | null,
			nextPageSize?: number,
			nextPageIndex?: number,
		) => {
			const params = filtersToSearchParams(nextFilters, nextSort, nextPageSize, nextPageIndex);
			setSearchParams(params, { replace: true });
		},
		[setSearchParams],
	);

	const debouncedSyncRef = useRef(debounce(syncToUrl, URL_SYNC_DEBOUNCE_MS));
	useEffect(() => {
		debouncedSyncRef.current = debounce(syncToUrl, URL_SYNC_DEBOUNCE_MS);
	}, [syncToUrl]);

	// Snapshot ref — lets callbacks read the latest state without being
	// recreated on every render (avoids infinite useCallback chains).
	const stateRef = useRef({ filters, sort, pageSize, pageIndex });
	stateRef.current = { filters, sort, pageSize, pageIndex };

	// Any filter/sort change resets pagination to the first page.
	const resetPagination = useCallback(() => {
		setPageIndex(0);
		setAfterCursor(undefined);
		cursorStackRef.current = [];
	}, []);

	// -- Filter callbacks -------------------------------------------------------

	const setFilter = useCallback(
		(field: string, value: ActiveFilterValue | undefined) => {
			const { sort: s, pageSize: ps } = stateRef.current;
			setFilters((prev) => {
				const next = prev.filter((f) => f.field !== field);
				if (value) next.push(value);
				debouncedSyncRef.current(next, s, ps);
				return next;
			});
			resetPagination();
		},
		[resetPagination],
	);

	const removeFilter = useCallback(
		(field: string) => {
			const { sort: s, pageSize: ps } = stateRef.current;
			setFilters((prev) => {
				const next = prev.filter((f) => f.field !== field);
				debouncedSyncRef.current(next, s, ps);
				return next;
			});
			resetPagination();
		},
		[resetPagination],
	);

	// -- Sort callback ----------------------------------------------------------

	const setSort = useCallback(
		(nextSort: SortState | null) => {
			const { filters: f, pageSize: ps } = stateRef.current;
			setLocalSort(nextSort);
			debouncedSyncRef.current(f, nextSort, ps);
			resetPagination();
		},
		[resetPagination],
	);

	// -- Reset ------------------------------------------------------------------

	const resetAll = useCallback(() => {
		setFilters([]);
		setLocalSort(null);
		resetPagination();
		syncToUrl([], null, defaultPageSize, 0);
		setPageSizeState(defaultPageSize);
	}, [syncToUrl, resetPagination]);

	// -- Pagination callbacks ---------------------------------------------------
	// Uses a cursor stack to track visited pages. "Next" pushes the current
	// endCursor onto the stack; "Previous" pops it to restore the prior cursor.

	const goToNextPage = useCallback((endCursor: string) => {
		cursorStackRef.current = [...cursorStackRef.current, endCursor];
		setAfterCursor(endCursor);
		setPageIndex((prev) => {
			const nextIndex = prev + 1;
			const { filters: f, sort: s, pageSize: ps } = stateRef.current;
			debouncedSyncRef.current(f, s, ps, nextIndex);
			return nextIndex;
		});
	}, []);

	const goToPreviousPage = useCallback(() => {
		const stack = cursorStackRef.current;
		const next = stack.slice(0, -1);
		cursorStackRef.current = next;
		setAfterCursor(next.length > 0 ? next[next.length - 1] : undefined);
		setPageIndex((prev) => {
			const nextIndex = Math.max(0, prev - 1);
			const { filters: f, sort: s, pageSize: ps } = stateRef.current;
			debouncedSyncRef.current(f, s, ps, nextIndex);
			return nextIndex;
		});
	}, []);

	const setPageSize = useCallback(
		(newSize: number) => {
			const validated = getValidPageSize(newSize);
			const { filters: f, sort: s } = stateRef.current;
			setPageSizeState(validated);
			resetPagination();
			debouncedSyncRef.current(f, s, validated);
		},
		[resetPagination],
	);

	// -- Derived query objects ---------------------------------------------------
	// Translate local filter/sort state into API-ready `where` and `orderBy`.

	const where = useMemo(
		() => buildFilter<TFilter>(filters, filterConfigs),
		[filters, filterConfigs],
	);

	const orderBy = useMemo(() => buildOrderBy<TOrderBy>(sort), [sort]);

	// -- Memoized return groups -------------------------------------------------
	// Each group is individually memoized so its object reference stays stable
	// unless the contained values change. This makes it safe to pass a group
	// (e.g. `pagination`) directly as props to a React.memo child without
	// causing unnecessary re-renders.

	const filtersGroup = useMemo(
		() => ({ active: filters, set: setFilter, remove: removeFilter }),
		[filters, setFilter, removeFilter],
	);

	const sortGroup = useMemo(() => ({ current: sort, set: setSort }), [sort, setSort]);

	const query = useMemo(() => ({ where, orderBy }), [where, orderBy]);

	const pagination = useMemo(
		() => ({ pageSize, pageIndex, afterCursor, setPageSize, goToNextPage, goToPreviousPage }),
		[pageSize, pageIndex, afterCursor, setPageSize, goToNextPage, goToPreviousPage],
	);

	return {
		filters: filtersGroup,
		sort: sortGroup,
		query,
		pagination,
		resetAll,
	};
}
