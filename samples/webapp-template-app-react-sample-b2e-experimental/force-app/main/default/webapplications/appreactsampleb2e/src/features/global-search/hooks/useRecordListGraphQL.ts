/**
 * Record list hook: GraphQL records with filter, sort, pagination, search.
 * Use for list/search views; detail view uses useRecordDetailLayout instead.
 *
 * @module hooks/useRecordListGraphQL
 */

import { useState, useEffect, useCallback } from "react";
import { useObjectColumns } from "./useObjectSearchData";
import {
	getRecordsGraphQL,
	buildOrderByFromSort,
	type RecordListGraphQLResult,
} from "../api/recordListGraphQLService";
import type { Column } from "../types/search/searchResults";
import type { FilterCriteria } from "../types/filters/filters";

const EMPTY_FILTERS: FilterCriteria[] = [];

export interface UseRecordListGraphQLOptions {
	objectApiName: string;
	first?: number;
	after?: string | null;
	filters?: FilterCriteria[];
	sortBy?: string;
	searchQuery?: string;
	/** When provided, skips useObjectColumns (use from parent e.g. useObjectListMetadata). */
	columns?: Column[];
	columnsLoading?: boolean;
	columnsError?: string | null;
}

export interface UseRecordListGraphQLReturn {
	data: RecordListGraphQLResult | null;
	edges: Array<{ node?: Record<string, unknown> }>;
	pageInfo: {
		hasNextPage?: boolean;
		hasPreviousPage?: boolean;
		endCursor?: string | null;
		startCursor?: string | null;
	} | null;
	loading: boolean;
	error: string | null;
	columnsLoading: boolean;
	columnsError: string | null;
	refetch: () => void;
}

/**
 * Fetches records via GraphQL for the given object with filter, sort, pagination, and search.
 */
export function useRecordListGraphQL(
	options: UseRecordListGraphQLOptions,
): UseRecordListGraphQLReturn {
	const {
		objectApiName,
		first = 50,
		after = null,
		filters = EMPTY_FILTERS,
		sortBy = "",
		searchQuery = "",
		columns: columnsProp,
		columnsLoading: columnsLoadingProp,
		columnsError: columnsErrorProp,
	} = options;

	const fromParent = columnsProp !== undefined;
	const fromHook = useObjectColumns(fromParent ? null : objectApiName);

	const columns = fromParent ? columnsProp : fromHook.columns;
	const columnsLoading = fromParent ? (columnsLoadingProp ?? false) : fromHook.columnsLoading;
	const columnsError = fromParent ? (columnsErrorProp ?? null) : fromHook.columnsError;

	const [data, setData] = useState<RecordListGraphQLResult | null>(null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const fetchRecords = useCallback(() => {
		if (columnsLoading || columnsError || columns.length === 0) return;

		setLoading(true);
		setError(null);
		const orderBy = buildOrderByFromSort(sortBy);

		getRecordsGraphQL({
			objectApiName,
			columns,
			first,
			after,
			filters,
			orderBy,
			searchQuery: searchQuery.trim() || undefined,
		})
			.then((result) => {
				setData(result);
			})
			.catch((err) => {
				setError(err instanceof Error ? err.message : "Failed to load records");
			})
			.finally(() => {
				setLoading(false);
			});
	}, [
		objectApiName,
		columns,
		columnsLoading,
		columnsError,
		first,
		after,
		filters,
		sortBy,
		searchQuery,
	]);

	useEffect(() => {
		if (!objectApiName || columnsLoading || columnsError) return;
		if (columns.length === 0 && !columnsLoading) return;
		fetchRecords();
	}, [objectApiName, columns, columnsLoading, columnsError, fetchRecords]);

	const objectData = data?.uiapi?.query?.[objectApiName];
	const edges = objectData?.edges ?? [];
	const pageInfo = objectData?.pageInfo ?? null;

	return {
		data,
		edges,
		pageInfo,
		loading: columnsLoading || loading,
		error: columnsError || error,
		columnsLoading,
		columnsError,
		refetch: fetchRecords,
	};
}
