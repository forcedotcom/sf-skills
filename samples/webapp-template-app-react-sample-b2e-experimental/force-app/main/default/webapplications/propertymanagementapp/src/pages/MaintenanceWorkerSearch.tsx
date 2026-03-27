import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
	searchMaintenanceWorkers,
	fetchDistinctMaintenanceWorkerType,
	type MaintenanceWorkerSearchNode,
} from "../api/maintenanceWorkers/maintenanceWorkerSearchService";
import { useCachedAsyncData } from "../features/object-search/hooks/useCachedAsyncData";
import {
	useObjectSearchParams,
	type UseObjectSearchParamsReturn,
} from "../features/object-search/hooks/useObjectSearchParams";
import type { FilterFieldConfig } from "../features/object-search/utils/filterUtils";
import type { SortFieldConfig } from "../features/object-search/utils/sortUtils";
import { PageHeader } from "../components/layout/PageHeader";
import { PageContainer } from "../components/layout/PageContainer";
import {
	FilterProvider,
	FilterResetButton,
} from "../features/object-search/components/FilterContext";
import { FilterRow } from "../components/layout/FilterRow";
import { SearchFilter } from "../features/object-search/components/filters/SearchFilter";
import { SelectFilter } from "../features/object-search/components/filters/SelectFilter";
import { TextFilter } from "../features/object-search/components/filters/TextFilter";
import { NumericRangeFilter } from "../features/object-search/components/filters/NumericRangeFilter";
import { DateFilter } from "../features/object-search/components/filters/DateFilter";
import { ObjectSearchErrorState } from "../components/shared/ObjectSearchErrorState";
import PaginationControls from "../features/object-search/components/PaginationControls";
import { WorkerDetailsModal } from "../components/maintenanceWorkers/WorkerDetailsModal";
import { Skeleton } from "../components/ui/skeleton";
import {
	Table,
	TableHeader,
	TableBody,
	TableRow,
	TableHead,
	TableCell,
} from "../components/ui/table";
import type {
	Maintenance_Worker__C_Filter,
	Maintenance_Worker__C_OrderBy,
} from "../api/graphql-operations-types";
import { PAGINATION_CONFIG } from "../lib/constants";

const FILTER_CONFIGS: FilterFieldConfig[] = [
	{
		field: "search",
		label: "Search",
		type: "search",
		searchFields: ["Name", "Phone__c"],
		placeholder: "By name, or phone...",
	},
	{ field: "Employment_Type__c", label: "Employment Type", type: "picklist" },
	{ field: "Location__c", label: "Location", type: "text", placeholder: "Location" },
	{ field: "Hourly_Rate__c", label: "Hourly Rate", type: "numeric" },
	{ field: "CreatedDate", label: "Created Date", type: "date" },
];

const SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Name" },
	{ field: "Employment_Type__c", label: "Employment Type" },
	{ field: "Hourly_Rate__c", label: "Hourly Rate" },
	{ field: "Rating__c", label: "Rating" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function MaintenanceWorkerSearch() {
	const [selectedWorker, setSelectedWorker] = useState<MaintenanceWorkerSearchNode | null>(null);

	const { data: typeOptions } = useCachedAsyncData(fetchDistinctMaintenanceWorkerType, [], {
		key: "distinctMaintenanceWorkerType",
		ttl: 30_000,
	});

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Maintenance_Worker__C_Filter,
		Maintenance_Worker__C_OrderBy
	>(FILTER_CONFIGS, SORT_CONFIGS, PAGINATION_CONFIG);

	const searchKey = `maintenance-workers:${JSON.stringify({ where: query.where, orderBy: query.orderBy, first: pagination.pageSize, after: pagination.afterCursor })}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchMaintenanceWorkers({
				where: query.where,
				orderBy: query.orderBy,
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, query.orderBy, pagination.pageSize, pagination.afterCursor],
		{ key: searchKey },
	);

	const validMaintenanceWorkerNodes = useMemo(
		() =>
			(data?.edges ?? []).reduce<MaintenanceWorkerSearchNode[]>((acc, edge) => {
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
				<PageHeader title="Maintenance Workers" description="View and filter maintenance workers" />
				<MaintenanceWorkerSearchFilters
					filters={filters}
					typeOptions={typeOptions ?? []}
					resetAll={resetAll}
				/>

				<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
					<Table>
						<MaintenanceWorkerSearchTableHeader />
						<TableBody>
							{loading && <MaintenanceWorkerSearchSkeleton pageSize={pagination.pageSize} />}

							{!loading && error && <MaintenanceWorkerSearchErrorState />}

							{!loading && !error && validMaintenanceWorkerNodes.length === 0 && (
								<MaintenanceWorkerSearchNoResults />
							)}

							{!loading && !error && validMaintenanceWorkerNodes.length > 0 && (
								<MaintenanceWorkerSearchTable
									workerNodes={validMaintenanceWorkerNodes}
									setSelectedWorker={setSelectedWorker}
								/>
							)}
						</TableBody>
					</Table>
				</div>

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

			{!loading && !error && selectedWorker && (
				<WorkerDetailsModal
					worker={selectedWorker}
					isOpen={!!selectedWorker}
					onClose={() => setSelectedWorker(null)}
				/>
			)}
		</>
	);
}

function MaintenanceWorkerSearchFilters({
	filters,
	typeOptions,
	resetAll,
}: {
	filters: UseObjectSearchParamsReturn<
		Maintenance_Worker__C_Filter,
		Maintenance_Worker__C_OrderBy
	>["filters"];
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
			<FilterRow ariaLabel="Maintenance Workers filters">
				<SearchFilter
					field="search"
					label="Search"
					placeholder="By name, or phone..."
					className="w-full sm:w-50"
				/>
				<SelectFilter
					field="Employment_Type__c"
					label="Employment Type"
					options={typeOptions}
					className="w-full sm:w-36"
				/>
				<TextFilter
					field="Location__c"
					label="Location"
					placeholder="Location"
					className="w-full sm:w-50"
				/>
				<NumericRangeFilter field="Hourly_Rate__c" label="Hourly Rate" className="w-full sm:w-50" />
				<DateFilter field="CreatedDate" label="Created Date" className="w-full sm:w-56" />
				<FilterResetButton />
			</FilterRow>
		</FilterProvider>
	);
}

function MaintenanceWorkerSearchTableHeader() {
	return (
		<TableHeader>
			<TableRow>
				<TableHead className="w-4/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Name
				</TableHead>
				<TableHead className="w-3/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Organization
				</TableHead>
				<TableHead className="w-3/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Active Requests
				</TableHead>
				<TableHead className="w-2/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Status
				</TableHead>
			</TableRow>
		</TableHeader>
	);
}

function MaintenanceWorkerSearchNoResults() {
	return (
		<TableRow>
			<TableCell colSpan={4} className="text-center py-12 text-gray-500">
				No maintenance workers found
			</TableCell>
		</TableRow>
	);
}

function MaintenanceWorkerSearchTable({
	workerNodes,
	setSelectedWorker,
}: {
	workerNodes: MaintenanceWorkerSearchNode[];
	setSelectedWorker: (worker: MaintenanceWorkerSearchNode) => void;
}) {
	return (
		<>
			{workerNodes.map((worker) => {
				const name = worker.Name?.value ?? "";
				const isActive = worker.IsActive__c?.value;
				return (
					<TableRow
						key={worker.Id}
						onClick={() => setSelectedWorker(worker)}
						className="hover:bg-gray-50 transition-colors cursor-pointer"
					>
						<TableCell className="px-6 py-4 font-medium text-gray-900">{name}</TableCell>
						<TableCell className="px-6 py-4 text-gray-600">
							{worker.Employment_Type__c?.value ?? worker.Type__c?.value ?? "\u2014"}
						</TableCell>
						<TableCell className="px-6 py-4 text-gray-600">
							{worker.Maintenance_Requests__r?.totalCount ?? 0}
						</TableCell>
						<TableCell className="px-6 py-4 text-gray-600">
							{typeof isActive === "boolean" ? (isActive ? "Active" : "Inactive") : "\u2014"}
						</TableCell>
					</TableRow>
				);
			})}
		</>
	);
}

function MaintenanceWorkerSearchSkeleton({ pageSize }: { pageSize: number }) {
	return (
		<>
			{Array.from({ length: pageSize }, (_, i) => (
				<TableRow key={i}>
					<TableCell className="w-4/12 px-6 py-4">
						<Skeleton className="h-5 w-3/4" />
					</TableCell>
					<TableCell className="w-3/12 px-6 py-4">
						<Skeleton className="h-5 w-2/3" />
					</TableCell>
					<TableCell className="w-3/12 px-6 py-4">
						<Skeleton className="h-5 w-1/4" />
					</TableCell>
					<TableCell className="w-2/12 px-6 py-4">
						<Skeleton className="h-5 w-1/2" />
					</TableCell>
				</TableRow>
			))}
		</>
	);
}

function MaintenanceWorkerSearchErrorState() {
	const navigate = useNavigate();

	return (
		<TableRow>
			<TableCell colSpan={4} className="p-0">
				<ObjectSearchErrorState
					message="There was an error loading the maintenance workers. Please try again."
					onGoHome={() => navigate("/")}
					onRetry={() => navigate(0)}
				/>
			</TableCell>
		</TableRow>
	);
}
