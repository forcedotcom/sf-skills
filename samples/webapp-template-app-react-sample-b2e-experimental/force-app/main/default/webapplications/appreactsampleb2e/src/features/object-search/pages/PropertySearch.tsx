import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
	searchProperties,
	fetchDistinctPropertyStatus,
	fetchDistinctPropertyType,
} from "../api/propertySearchService";
import { useCachedAsyncData } from "../hooks/useCachedAsyncData";
import { useObjectSearchParams } from "../hooks/useObjectSearchParams";
import {
	useCursorBasedAccumulation,
	type CursorBasedData,
} from "../hooks/useCursorBasedAccumulation";
import type { FilterFieldConfig } from "../utils/filterUtils";
import type { SortFieldConfig } from "../utils/sortUtils";
import type { PropertySearchResult } from "../api/propertySearchService";
import type { PaginationConfig } from "../hooks/useObjectSearchParams";
import { PageHeader } from "../../../components/layout/PageHeader";
import { PageContainer } from "../../../components/layout/PageContainer";
import { ObjectSearchFilterRow } from "../components/ObjectSearchFilterRow";
import { ObjectSearchErrorState } from "../components/ObjectSearchErrorState";
import { ObjectSearchLoadingState } from "../components/ObjectSearchLoadingState";
import PaginationControls from "../components/PaginationControls";
import { PropertyCard } from "../../../components/PropertyCard";
import { PropertyDetailsModal } from "../../../components/PropertyDetailsModal";
import { Skeleton } from "../../../components/ui/skeleton";
import { nodeToProperty } from "../../../lib/propertyAdapter";
import type { Property } from "../../../lib/types";

const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 12,
	validPageSizes: [6, 12, 24, 48],
};

type PropertyNode = NonNullable<
	NonNullable<NonNullable<PropertySearchResult["edges"]>[number]>["node"]
>;

function buildPropertyFilterConfigs(
	statusOptions: Array<{ value: string; label: string }>,
	typeOptions: Array<{ value: string; label: string }>,
): FilterFieldConfig[] {
	return [
		{
			field: "search",
			label: "Search",
			type: "search",
			searchFields: ["Name", "Address__c"],
			placeholder: "Search by name or address...",
		},
		{ field: "Name", label: "Property Name", type: "text", placeholder: "Search by name..." },
		{ field: "Status__c", label: "Status", type: "picklist", options: statusOptions },
		{ field: "Type__c", label: "Type", type: "picklist", options: typeOptions },
		{ field: "Monthly_Rent__c", label: "Monthly Rent", type: "numeric" },
		{ field: "Bedrooms__c", label: "Bedrooms", type: "numeric" },
	];
}

const PROPERTY_SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Name" },
	{ field: "Monthly_Rent__c", label: "Monthly Rent" },
	{ field: "Status__c", label: "Status" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function PropertySearch() {
	const navigate = useNavigate();
	const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
	const [retryCount, setRetryCount] = useState(0);

	const { data: statusOptions } = useCachedAsyncData(fetchDistinctPropertyStatus, [], {
		key: "distinctPropertyStatus",
		ttl: 300_000,
	});
	const { data: typeOptions } = useCachedAsyncData(fetchDistinctPropertyType, [], {
		key: "distinctPropertyType",
		ttl: 300_000,
	});

	const filterConfigs = useMemo(
		() => buildPropertyFilterConfigs(statusOptions ?? [], typeOptions ?? []),
		[statusOptions, typeOptions],
	);

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Record<string, unknown>,
		Record<string, unknown>
	>(filterConfigs, PROPERTY_SORT_CONFIGS, PAGINATION_CONFIG);

	const queryKey = useMemo(
		() => JSON.stringify({ where: query.where, orderBy: query.orderBy }),
		[query.where, query.orderBy],
	);

	const searchKey = `properties:${JSON.stringify({ where: query.where, orderBy: query.orderBy, first: pagination.pageSize, after: pagination.afterCursor })}:${retryCount}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchProperties({
				where: query.where,
				orderBy: query.orderBy,
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, query.orderBy, pagination.pageSize, pagination.afterCursor, retryCount],
		{ key: searchKey },
	);

	const {
		accumulatedItems: accumulatedNodes,
		loadMoreLoading,
		hasNextPage,
		onLoadMore,
	} = useCursorBasedAccumulation<PropertyNode>({
		data: data as CursorBasedData<PropertyNode> | undefined,
		loading,
		isFirstPage: !pagination.afterCursor,
		goToNextPage: pagination.goToNextPage,
		resetDeps: [queryKey],
	});

	const accumulatedProperties = useMemo(
		() => accumulatedNodes.map((node) => nodeToProperty(node as Record<string, unknown>)),
		[accumulatedNodes],
	);

	const filterRow = (
		<ObjectSearchFilterRow
			configs={filterConfigs}
			activeFilters={filters.active}
			onFilterChange={filters.set}
			onFilterRemove={filters.remove}
			onReset={resetAll}
			ariaLabel="Properties filters"
		/>
	);

	if (error && accumulatedProperties.length === 0) {
		return (
			<ObjectSearchErrorState
				title="Properties"
				description="Browse and manage available properties"
				filterRow={filterRow}
				message="There was an error loading the properties. Please try again."
				onGoHome={() => navigate("/")}
				onRetry={() => setRetryCount((c) => c + 1)}
			/>
		);
	}

	if (loading && accumulatedProperties.length === 0) {
		return (
			<ObjectSearchLoadingState
				title="Properties"
				description="Browse and manage available properties"
				filterRow={filterRow}
			>
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
					{Array.from({ length: pagination.pageSize }, (_, i) => (
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
			</ObjectSearchLoadingState>
		);
	}

	return (
		<>
			<PageHeader title="Properties" description="Browse and manage available properties" />
			<PageContainer>
				<div className="max-w-7xl mx-auto space-y-6">
					{filterRow}

					{accumulatedProperties.length === 0 ? (
						<div className="text-center py-12">
							<p className="text-gray-500 text-lg">No properties found</p>
						</div>
					) : (
						<>
							<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
								{accumulatedProperties.map((property) => (
									<PropertyCard
										key={property.id}
										property={property}
										onClick={setSelectedProperty}
									/>
								))}
							</div>
							<PaginationControls
								variant="loadMore"
								pageSize={pagination.pageSize}
								pageSizeOptions={PAGINATION_CONFIG.validPageSizes}
								onPageSizeChange={pagination.setPageSize}
								hasNextPage={hasNextPage}
								onLoadMore={onLoadMore}
								loadMoreLoading={loadMoreLoading}
							/>
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
