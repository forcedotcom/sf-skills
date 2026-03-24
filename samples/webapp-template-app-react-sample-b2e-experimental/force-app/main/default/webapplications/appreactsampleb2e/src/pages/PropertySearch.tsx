import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
	searchProperties,
	fetchDistinctPropertyStatus,
	fetchDistinctPropertyType,
	type PropertySearchNode,
} from "../api/properties/propertySearchService";
import { useCachedAsyncData } from "../features/object-search/hooks/useCachedAsyncData";
import {
	useObjectSearchParams,
	type UseObjectSearchParamsReturn,
} from "../features/object-search/hooks/useObjectSearchParams";
import type { FilterFieldConfig } from "../features/object-search/utils/filterUtils";
import type { SortFieldConfig } from "../features/object-search/utils/sortUtils";
import type { Property__C_Filter, Property__C_OrderBy } from "../api/graphql-operations-types";
import { PageHeader } from "../components/layout/PageHeader";
import { PageContainer } from "../components/layout/PageContainer";
import {
	FilterProvider,
	FilterResetButton,
} from "../features/object-search/components/FilterContext";
import { FilterRow } from "../components/layout/FilterRow";
import { SearchFilter } from "../features/object-search/components/filters/SearchFilter";
import { SelectFilter } from "../features/object-search/components/filters/SelectFilter";
import { NumericRangeFilter } from "../features/object-search/components/filters/NumericRangeFilter";
import { ObjectSearchErrorState } from "../components/shared/ObjectSearchErrorState";
import PaginationControls from "../features/object-search/components/PaginationControls";
import { PropertyCard } from "../components/properties/PropertyCard";
import { PropertyDetailsModal } from "../components/properties/PropertyDetailsModal";
import { Skeleton } from "../components/ui/skeleton";
import { PAGINATION_CONFIG } from "../lib/constants";

const FILTER_CONFIGS: FilterFieldConfig[] = [
	{
		field: "search",
		label: "Search",
		type: "search",
		searchFields: ["Name", "Address__c"],
		placeholder: "Search by name or address...",
	},
	{ field: "Name", label: "Property Name", type: "text", placeholder: "Search by name..." },
	{ field: "Status__c", label: "Status", type: "picklist" },
	{ field: "Type__c", label: "Type", type: "picklist" },
	{ field: "Monthly_Rent__c", label: "Monthly Rent", type: "numeric" },
	{ field: "Bedrooms__c", label: "Bedrooms", type: "numeric" },
];

const PROPERTY_SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Name" },
	{ field: "Monthly_Rent__c", label: "Monthly Rent" },
	{ field: "Status__c", label: "Status" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function PropertySearch() {
	const [selectedProperty, setSelectedProperty] = useState<PropertySearchNode | null>(null);

	const { data: statusOptions } = useCachedAsyncData(fetchDistinctPropertyStatus, [], {
		key: "distinctPropertyStatus",
		ttl: 30_000,
	});
	const { data: typeOptions } = useCachedAsyncData(fetchDistinctPropertyType, [], {
		key: "distinctPropertyType",
		ttl: 30_000,
	});

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Property__C_Filter,
		Property__C_OrderBy
	>(FILTER_CONFIGS, PROPERTY_SORT_CONFIGS, PAGINATION_CONFIG);

	const searchKey = `properties:${JSON.stringify({ where: query.where, orderBy: query.orderBy, first: pagination.pageSize, after: pagination.afterCursor })}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchProperties({
				where: query.where,
				orderBy: query.orderBy,
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, query.orderBy, pagination.pageSize, pagination.afterCursor],
		{ key: searchKey },
	);

	const validPropertyNodes = useMemo(
		() =>
			(data?.edges ?? []).reduce<PropertySearchNode[]>((acc, edge) => {
				if (edge?.node) acc.push(edge.node);
				return acc;
			}, []),
		[data?.edges],
	);

	const pageInfo = data?.pageInfo;
	const hasNextPage = pageInfo?.hasNextPage ?? false;
	const hasPreviousPage = pagination.pageIndex > 0;

	return (
		<>
			<PageContainer>
				<PageHeader title="Properties" description="Browse and manage available properties" />
				<PropertySearchFilters
					filters={filters}
					statusOptions={statusOptions ?? []}
					typeOptions={typeOptions ?? []}
					resetAll={resetAll}
				/>

				{loading && <PropertySearchSkeleton pageSize={pagination.pageSize} />}

				{!loading && error && <PropertySearchErrorState />}

				{!loading && !error && validPropertyNodes.length === 0 && <PropertySearchNoResults />}

				{!loading && !error && validPropertyNodes.length > 0 && (
					<PropertySearchGrid
						propertyNodes={validPropertyNodes}
						setSelectedProperty={setSelectedProperty}
					/>
				)}

				<PaginationControls
					pageIndex={pagination.pageIndex}
					hasNextPage={hasNextPage}
					hasPreviousPage={hasPreviousPage}
					pageSize={pagination.pageSize}
					pageSizeOptions={PAGINATION_CONFIG.validPageSizes}
					onNextPage={() => {
						if (pageInfo?.endCursor) pagination.goToNextPage(pageInfo.endCursor);
					}}
					onPreviousPage={pagination.goToPreviousPage}
					onPageSizeChange={pagination.setPageSize}
					disabled={loading || !!error}
				/>
			</PageContainer>

			{!loading && !error && selectedProperty && (
				<PropertyDetailsModal
					property={selectedProperty}
					isOpen={!!selectedProperty}
					onClose={() => setSelectedProperty(null)}
				/>
			)}
		</>
	);
}

function PropertySearchFilters({
	filters,
	statusOptions,
	typeOptions,
	resetAll,
}: {
	filters: UseObjectSearchParamsReturn<Property__C_Filter, Property__C_OrderBy>["filters"];
	statusOptions: Array<{ value: string; label: string }>;
	typeOptions: Array<{ value: string; label: string }>;
	resetAll: () => void;
}) {
	return (
		<FilterProvider
			filters={filters.active}
			onFilterChange={filters.set}
			onFilterRemove={filters.remove}
			onReset={resetAll}
		>
			<FilterRow ariaLabel="Properties filters">
				<SearchFilter
					field="search"
					label="Search"
					placeholder="Search by name or address..."
					className="w-full sm:w-50"
				/>
				<SelectFilter
					field="Status__c"
					label="Status"
					options={statusOptions}
					className="w-full sm:w-36"
				/>
				<SelectFilter
					field="Type__c"
					label="Type"
					options={typeOptions}
					className="w-full sm:w-36"
				/>
				<NumericRangeFilter
					field="Monthly_Rent__c"
					label="Monthly Rent"
					className="w-full sm:w-50"
				/>
				<NumericRangeFilter field="Bedrooms__c" label="Bedrooms" className="w-full sm:w-50" />
				<FilterResetButton />
			</FilterRow>
		</FilterProvider>
	);
}

function PropertySearchNoResults() {
	return (
		<div className="text-center py-12">
			<p className="text-gray-500 text-lg">No properties found</p>
		</div>
	);
}

function PropertySearchGrid({
	propertyNodes,
	setSelectedProperty,
}: {
	propertyNodes: PropertySearchNode[];
	setSelectedProperty: (property: PropertySearchNode) => void;
}) {
	return (
		<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{propertyNodes.map((property) => (
				<PropertyCard key={property.Id} property={property} onClick={setSelectedProperty} />
			))}
		</div>
	);
}

function PropertySearchSkeleton({ pageSize }: { pageSize: number }) {
	return (
		<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{Array.from({ length: pageSize }, (_, i) => (
				<div key={i} className="bg-white rounded-lg shadow-md overflow-hidden">
					<Skeleton className="h-48 w-full rounded-none" />
					<div className="p-6 space-y-2">
						<Skeleton className="h-6 w-48" />
						<Skeleton className="h-4 w-full" />
						<Skeleton className="h-4 w-40" />
						<Skeleton className="h-4 w-24" />
					</div>
				</div>
			))}
		</div>
	);
}

function PropertySearchErrorState() {
	const navigate = useNavigate();

	return (
		<ObjectSearchErrorState
			message="There was an error loading the properties. Please try again."
			onGoHome={() => navigate("/")}
			onRetry={() => navigate(0)}
		/>
	);
}
