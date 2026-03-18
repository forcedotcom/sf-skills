import { useEffect, useState, useRef, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router";
import { type FilterCriteria } from "../features/global-search/types/filters/filters";
import { useObjectListMetadata } from "../features/global-search/hooks/useObjectSearchData";
import { useRecordListGraphQL } from "../features/global-search/hooks/useRecordListGraphQL";

import type { Property } from "../lib/types";
import { PropertyCard } from "../components/PropertyCard";
import { PropertyDetailsModal } from "../components/PropertyDetailsModal";
import { PageContainer } from "../components/layout/PageContainer";
import { PageHeader } from "../components/layout/PageHeader";
import { PageLoadingState } from "../components/feedback/PageLoadingState";
import { PageErrorState } from "../components/feedback/PageErrorState";
import { FilterErrorAlert } from "../components/feedback/FilterErrorAlert";
import { ListPageFilterRow } from "../components/filters/ListPageFilterRow";
import { GLOBAL_SEARCH_OBJECT_API_NAME } from "../lib/globalSearchConstants";
import { nodeToProperty } from "../lib/propertyAdapter";
import { getPropertyListColumns } from "../lib/propertyColumns";
import {
	buildFilterCriteriaFromFormValues,
	getDefaultFilterFormValues,
	getApplicableFilters,
} from "../lib/filterUtils";
import { PAGE_SIZE_LIST, PROPERTY_FILTER_EXCLUDED_FIELD_PATHS } from "../lib/constants";
import { useAccumulatedListPages } from "../hooks/useAccumulatedListPages";

const PROPERTIES_DEFAULT_SORT = "CreatedDate DESC";

const mapNodeToProperty = (node: unknown) =>
	nodeToProperty(node as Record<string, unknown> | undefined);

export default function Properties() {
	const [searchParams] = useSearchParams();
	const searchQuery = searchParams.get("q") ?? "";

	const [afterCursor, setAfterCursor] = useState<string | null>(null);
	const [appliedFilters, setAppliedFilters] = useState<FilterCriteria[]>([]);
	const [filterFormValues, setFilterFormValues] = useState<Record<string, string>>({});
	const [filterError, setFilterError] = useState<string | null>(null);
	const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
	const hasInitializedFiltersRef = useRef(false);

	const listMeta = useObjectListMetadata(GLOBAL_SEARCH_OBJECT_API_NAME);
	const columns = useMemo(() => getPropertyListColumns(listMeta.columns), [listMeta.columns]);
	const filters = useMemo(
		() => getApplicableFilters(listMeta.filters ?? [], PROPERTY_FILTER_EXCLUDED_FIELD_PATHS),
		[listMeta.filters],
	);
	const picklistValues = listMeta.picklistValues ?? {};

	const {
		edges,
		pageInfo,
		loading: resultsLoading,
		error: resultsError,
	} = useRecordListGraphQL({
		objectApiName: GLOBAL_SEARCH_OBJECT_API_NAME,
		columns,
		columnsLoading: listMeta.loading,
		columnsError: listMeta.error,
		first: PAGE_SIZE_LIST,
		after: afterCursor,
		searchQuery: searchQuery.trim() || undefined,
		sortBy: PROPERTIES_DEFAULT_SORT,
		filters: appliedFilters,
	});

	const [accumulated, setAccumulated] = useAccumulatedListPages(
		edges,
		resultsLoading,
		afterCursor,
		mapNodeToProperty,
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
	}, [searchQuery, appliedFilters, setAccumulated]);

	const hasNextPage = Boolean(pageInfo?.hasNextPage);
	const endCursor = pageInfo?.endCursor ?? null;

	const handleLoadMore = useCallback(() => {
		if (endCursor && !searchQuery.trim()) setAfterCursor(endCursor);
	}, [endCursor, searchQuery]);

	const handlePropertyClick = useCallback((property: Property) => {
		setSelectedProperty(property);
	}, []);

	const handleApplyFilters = useCallback(() => {
		setFilterError(null);
		const result = buildFilterCriteriaFromFormValues(
			GLOBAL_SEARCH_OBJECT_API_NAME,
			filters,
			filterFormValues,
		);
		if (result.rangeError) {
			setFilterError(result.rangeError);
			return;
		}
		setAppliedFilters(result.criteria);
		setAfterCursor(null);
	}, [filters, filterFormValues]);

	const handleResetFilters = useCallback(() => {
		setFilterFormValues(getDefaultFilterFormValues(filters));
		setAppliedFilters([]);
		setAfterCursor(null);
		setFilterError(null);
	}, [filters]);

	const handleFilterFormValueChange = useCallback((key: string, value: string) => {
		setFilterFormValues((prev) => ({ ...prev, [key]: value }));
		setFilterError(null);
	}, []);

	const loading = listMeta.loading || resultsLoading;
	const error = listMeta.error ?? resultsError;

	if (error) {
		return <PageErrorState message={error} />;
	}

	if (loading && accumulated.length === 0) {
		return <PageLoadingState message="Loading properties..." />;
	}

	return (
		<>
			<PageHeader title="Properties" description="Browse and manage available properties" />
			<PageContainer>
				<div className="max-w-7xl mx-auto space-y-6">
					<ListPageFilterRow
						filters={filters}
						picklistValues={picklistValues}
						formValues={filterFormValues}
						onFormValueChange={handleFilterFormValueChange}
						onApply={handleApplyFilters}
						onReset={handleResetFilters}
						ariaLabel="Properties filters"
					/>
					{filterError && <FilterErrorAlert message={filterError} />}

					{accumulated.length === 0 ? (
						<div className="text-center py-12">
							<p className="text-gray-500 text-lg">No properties found</p>
						</div>
					) : (
						<>
							<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
								{accumulated.map((property) => (
									<PropertyCard
										key={property.id}
										property={property}
										onClick={handlePropertyClick}
									/>
								))}
							</div>
							{hasNextPage && !searchQuery.trim() && (
								<div className="flex justify-center mt-6">
									<button
										type="button"
										onClick={handleLoadMore}
										disabled={resultsLoading}
										className="px-6 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-lg text-sm font-medium disabled:opacity-50"
									>
										{resultsLoading ? "Loading..." : "Load More"}
									</button>
								</div>
							)}
						</>
					)}
				</div>

				{selectedProperty && (
					<PropertyDetailsModal
						property={selectedProperty}
						isOpen={!!selectedProperty}
						onClose={() => setSelectedProperty(null)}
					/>
				)}
			</PageContainer>
		</>
	);
}
