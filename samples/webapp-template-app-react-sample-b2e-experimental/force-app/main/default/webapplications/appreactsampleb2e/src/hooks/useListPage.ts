import { useEffect, useState, useRef, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router";
import { useObjectListMetadata } from "../features/global-search/hooks/useObjectSearchData";
import type { FilterCriteria } from "../features/global-search/types/filters/filters";
import { useRecordListGraphQL } from "../features/global-search/hooks/useRecordListGraphQL";
import { PAGE_SIZE_LIST } from "../lib/constants";
import {
	buildFilterCriteriaFromFormValues,
	getDefaultFilterFormValues,
	getApplicableFilters,
} from "../lib/filterUtils";
import { useAccumulatedListPages } from "./useAccumulatedListPages";
import type { ListPageConfig } from "../lib/listPageConfig";

/** Picklist option shape from useObjectListMetadata (label/value). */
export interface PicklistOption {
	label?: string;
	value: string;
}

export interface UseListPageResult<T> {
	filters: ReturnType<typeof getApplicableFilters>;
	picklistValues: Record<string, PicklistOption[]>;
	formValues: Record<string, string>;
	onFormValueChange: (key: string, value: string) => void;
	onApplyFilters: () => void;
	onResetFilters: () => void;
	filterError: string | null;
	loading: boolean;
	error: string | null;
	items: T[];
	canLoadMore: boolean;
	onLoadMore: () => void;
	loadMoreLoading: boolean;
	sortBy?: string;
	onSortChange?: (sortBy: string) => void;
}

/**
 * Shared hook for list pages with API-driven filters and GraphQL data.
 * Uses useObjectListMetadata and useRecordListGraphQL; search comes from URL ?q=.
 * Pass the returned props to ListPageWithFilters and render your table/list as children.
 */
export function useListPage<T>(config: ListPageConfig<T>): UseListPageResult<T> {
	const [searchParams] = useSearchParams();
	const searchQuery = searchParams.get("q") ?? "";

	const [afterCursor, setAfterCursor] = useState<string | null>(null);
	const [appliedFilters, setAppliedFilters] = useState<FilterCriteria[]>([]);
	const [filterFormValues, setFilterFormValues] = useState<Record<string, string>>({});
	const [filterError, setFilterError] = useState<string | null>(null);
	const hasInitializedFiltersRef = useRef(false);
	const [sortBy, setSortBy] = useState(config.defaultSort);

	const listMeta = useObjectListMetadata(config.objectApiName);
	const columns = useMemo(() => config.getColumns(listMeta.columns), [listMeta.columns, config]);
	const filters = useMemo(
		() => getApplicableFilters(listMeta.filters ?? [], config.filterExcludedFieldPaths),
		[listMeta.filters, config.filterExcludedFieldPaths],
	);
	const picklistValues = listMeta.picklistValues ?? {};

	const effectiveSort = config.sortable ? sortBy : config.defaultSort;

	const {
		edges,
		pageInfo,
		loading: resultsLoading,
		error: resultsError,
	} = useRecordListGraphQL({
		objectApiName: config.objectApiName,
		columns,
		columnsLoading: listMeta.loading,
		columnsError: listMeta.error,
		first: PAGE_SIZE_LIST,
		after: afterCursor,
		searchQuery: searchQuery.trim() || undefined,
		sortBy: effectiveSort,
		filters: appliedFilters,
	});

	const mapNode = useCallback((node: unknown) => config.nodeToItem(node), [config]);

	const [accumulated, setAccumulated] = useAccumulatedListPages(
		edges,
		resultsLoading,
		afterCursor,
		mapNode,
	);

	useEffect(() => {
		if (filters.length === 0) return;
		if (!hasInitializedFiltersRef.current) {
			hasInitializedFiltersRef.current = true;
			setFilterFormValues(getDefaultFilterFormValues(filters));
		}
	}, [filters]);

	useEffect(() => {
		setAfterCursor(null);
		setAccumulated([]);
	}, [searchQuery, appliedFilters, effectiveSort, setAccumulated]);

	const loading = listMeta.loading || resultsLoading;
	const error = listMeta.error ?? resultsError ?? null;
	const hasNextPage = Boolean(pageInfo?.hasNextPage);
	const endCursor = pageInfo?.endCursor ?? null;

	const onLoadMore = useCallback(() => {
		if (endCursor && !searchQuery.trim()) setAfterCursor(endCursor);
	}, [endCursor, searchQuery]);

	const onApplyFilters = useCallback(() => {
		setFilterError(null);
		const result = buildFilterCriteriaFromFormValues(
			config.objectApiName,
			filters,
			filterFormValues,
		);
		if (result.rangeError) {
			setFilterError(result.rangeError);
			return;
		}
		setAppliedFilters(result.criteria);
		setAfterCursor(null);
	}, [config.objectApiName, filters, filterFormValues]);

	const onResetFilters = useCallback(() => {
		setFilterFormValues(getDefaultFilterFormValues(filters));
		setAppliedFilters([]);
		setAfterCursor(null);
		setFilterError(null);
	}, [filters]);

	const onFormValueChange = useCallback((key: string, value: string) => {
		setFilterFormValues((prev) => ({ ...prev, [key]: value }));
		setFilterError(null);
	}, []);

	const onSortChange = useCallback((newSortBy: string) => {
		setSortBy(newSortBy);
		setAfterCursor(null);
	}, []);

	const result: UseListPageResult<T> = {
		filters,
		picklistValues: picklistValues as Record<string, PicklistOption[]>,
		formValues: filterFormValues,
		onFormValueChange,
		onApplyFilters,
		onResetFilters,
		filterError,
		loading,
		error,
		items: accumulated,
		canLoadMore: hasNextPage && !searchQuery.trim(),
		onLoadMore,
		loadMoreLoading: resultsLoading,
	};
	if (config.sortable) {
		result.sortBy = sortBy;
		result.onSortChange = onSortChange;
	}
	return result;
}
