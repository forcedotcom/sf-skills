import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { ChevronDown } from "lucide-react";
import { toast } from "../../../components/ui/sonner";
import {
	searchMaintenanceRequests,
	fetchDistinctMaintenanceRequestStatus,
	fetchDistinctMaintenanceRequestType,
	fetchDistinctMaintenanceRequestPriority,
} from "../api/maintenanceRequestSearchService";
import { useCachedAsyncData } from "../hooks/useCachedAsyncData";
import { useObjectSearchParams } from "../hooks/useObjectSearchParams";
import {
	useCursorBasedAccumulation,
	type CursorBasedData,
} from "../hooks/useCursorBasedAccumulation";
import type { FilterFieldConfig } from "../utils/filterUtils";
import type { SortFieldConfig } from "../utils/sortUtils";
import type { MaintenanceRequestSearchResult } from "../api/maintenanceRequestSearchService";
import type { PaginationConfig } from "../hooks/useObjectSearchParams";
import { PageHeader } from "../../../components/layout/PageHeader";
import { PageContainer } from "../../../components/layout/PageContainer";
import { ObjectSearchFilterRow } from "../components/ObjectSearchFilterRow";
import { ObjectSearchErrorState } from "../components/ObjectSearchErrorState";
import { ObjectSearchLoadingState } from "../components/ObjectSearchLoadingState";
import PaginationControls from "../components/PaginationControls";
import { UserAvatar } from "../../../components/UserAvatar";
import { Skeleton } from "../../../components/ui/skeleton";
import { StatusBadge } from "../../../components/StatusBadge";
import { MaintenanceDetailsModal } from "../../../components/MaintenanceDetailsModal";
import { nodeToMaintenanceRequest } from "../../../lib/maintenanceAdapter";
import { updateMaintenanceStatus } from "../../../api/maintenance";
import type { MaintenanceRequest } from "../../../lib/types";
import PlumbingIcon from "../../../assets/icons/plumbing.svg";
import HVACIcon from "../../../assets/icons/hvac.svg";
import ElectricalIcon from "../../../assets/icons/electrical.svg";
import AppliancesIcon from "../../../assets/icons/appliances.svg";
import PestIcon from "../../../assets/icons/pest.svg";

const issueIcons: Record<string, string> = {
	Plumbing: PlumbingIcon,
	HVAC: HVACIcon,
	Electrical: ElectricalIcon,
	Appliance: AppliancesIcon,
	Pest: PestIcon,
};

const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 12,
	validPageSizes: [6, 12, 24, 48],
};

type MaintenanceRequestNode = NonNullable<
	NonNullable<NonNullable<MaintenanceRequestSearchResult["edges"]>[number]>["node"]
>;

function buildFilterConfigs(
	statusOptions: Array<{ value: string; label: string }>,
	typeOptions: Array<{ value: string; label: string }>,
	priorityOptions: Array<{ value: string; label: string }>,
): FilterFieldConfig[] {
	return [
		{
			field: "search",
			label: "Search",
			type: "search",
			searchFields: ["Name", "Description__c"],
			placeholder: "Search by subject or description...",
		},
		{ field: "Status__c", label: "Status", type: "picklist", options: statusOptions },
		{ field: "Type__c", label: "Type", type: "picklist", options: typeOptions },
		{ field: "Priority__c", label: "Priority", type: "picklist", options: priorityOptions },
		{ field: "Scheduled__c", label: "Scheduled", type: "date" },
	];
}

const SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Subject" },
	{ field: "Status__c", label: "Status" },
	{ field: "Priority__c", label: "Priority" },
	{ field: "Scheduled__c", label: "Scheduled" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function MaintenanceRequestSearch() {
	const navigate = useNavigate();
	const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequest | null>(null);
	const [retryCount, setRetryCount] = useState(0);

	const { data: statusOptions } = useCachedAsyncData(fetchDistinctMaintenanceRequestStatus, [], {
		key: "distinctMaintenanceRequestStatus",
		ttl: 300_000,
	});
	const { data: typeOptions } = useCachedAsyncData(fetchDistinctMaintenanceRequestType, [], {
		key: "distinctMaintenanceRequestType",
		ttl: 300_000,
	});
	const { data: priorityOptions } = useCachedAsyncData(
		fetchDistinctMaintenanceRequestPriority,
		[],
		{ key: "distinctMaintenanceRequestPriority", ttl: 300_000 },
	);

	const filterConfigs = useMemo(
		() => buildFilterConfigs(statusOptions ?? [], typeOptions ?? [], priorityOptions ?? []),
		[statusOptions, typeOptions, priorityOptions],
	);

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Record<string, unknown>,
		Record<string, unknown>
	>(filterConfigs, SORT_CONFIGS, PAGINATION_CONFIG);

	const queryKey = useMemo(
		() => JSON.stringify({ where: query.where, orderBy: query.orderBy }),
		[query.where, query.orderBy],
	);

	const searchKey = `maintenance-requests:${JSON.stringify({ where: query.where, orderBy: query.orderBy, first: pagination.pageSize, after: pagination.afterCursor })}:${retryCount}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchMaintenanceRequests({
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
	} = useCursorBasedAccumulation<MaintenanceRequestNode>({
		data: data as CursorBasedData<MaintenanceRequestNode> | undefined,
		loading,
		isFirstPage: !pagination.afterCursor,
		goToNextPage: pagination.goToNextPage,
		resetDeps: [queryKey],
	});

	const accumulatedRequests = useMemo(
		() => accumulatedNodes.map((node) => nodeToMaintenanceRequest(node as Record<string, unknown>)),
		[accumulatedNodes],
	);

	const handleSaveStatus = async (requestId: string, status: string) => {
		try {
			const success = await updateMaintenanceStatus(requestId, status);
			if (success) {
				if (selectedRequest?.id === requestId) {
					setSelectedRequest({ ...selectedRequest, status });
				}
				toast.success("Status updated", {
					description: "Maintenance request status has been updated successfully.",
				});
			} else {
				toast.error("Update failed", {
					description: "Failed to update maintenance request status. Please try again.",
				});
			}
		} catch (err) {
			console.error(err);
			toast.error("Error updating status", {
				description: "An error occurred while updating the status. Please try again.",
			});
		}
	};

	const filterRow = (
		<ObjectSearchFilterRow
			configs={filterConfigs}
			activeFilters={filters.active}
			onFilterChange={filters.set}
			onFilterRemove={filters.remove}
			onReset={resetAll}
			ariaLabel="Maintenance Requests filters"
		/>
	);

	if (error && accumulatedRequests.length === 0) {
		return (
			<ObjectSearchErrorState
				title="Maintenance Requests"
				description="Track and manage maintenance requests"
				filterRow={filterRow}
				message="There was an error loading the maintenance requests. Please try again."
				onGoHome={() => navigate("/")}
				onRetry={() => setRetryCount((c) => c + 1)}
			/>
		);
	}

	if (loading && accumulatedRequests.length === 0) {
		return (
			<ObjectSearchLoadingState
				title="Maintenance Requests"
				description="Track and manage maintenance requests"
				filterRow={filterRow}
			>
				<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
					<div className="grid grid-cols-12 gap-4 px-6 py-4 bg-gray-50 border-b border-gray-200">
						<div className="col-span-4">
							<Skeleton className="h-4 w-28" />
						</div>
						<div className="col-span-3">
							<Skeleton className="h-4 w-24" />
						</div>
						<div className="col-span-3">
							<Skeleton className="h-4 w-28" />
						</div>
						<div className="col-span-2">
							<Skeleton className="h-4 w-14" />
						</div>
					</div>
					<div className="divide-y divide-gray-200">
						{Array.from({ length: pagination.pageSize }, (_, i) => (
							<div key={i} className="grid grid-cols-12 gap-4 px-6 py-5">
								<div className="col-span-4 flex items-center gap-4">
									<Skeleton className="h-16 w-16 rounded-lg shrink-0" />
									<div className="space-y-2 flex-1 min-w-0">
										<Skeleton className="h-4 w-full" />
										<Skeleton className="h-3 w-20" />
									</div>
								</div>
								<div className="col-span-3 flex items-center gap-3">
									<Skeleton className="h-10 w-10 rounded-full shrink-0" />
									<div className="space-y-2 min-w-0">
										<Skeleton className="h-4 w-24" />
										<Skeleton className="h-3 w-32" />
									</div>
								</div>
								<div className="col-span-3 flex items-center">
									<Skeleton className="h-4 w-28" />
								</div>
								<div className="col-span-2 flex items-center">
									<Skeleton className="h-6 w-20 rounded-full" />
								</div>
							</div>
						))}
					</div>
				</div>
			</ObjectSearchLoadingState>
		);
	}

	return (
		<>
			<PageHeader
				title="Maintenance Requests"
				description="Track and manage maintenance requests"
			/>

			<PageContainer>
				<div className="max-w-7xl mx-auto space-y-6">
					{filterRow}

					{accumulatedRequests.length === 0 ? (
						<div className="text-center py-12 text-gray-500">No maintenance requests found</div>
					) : (
						<>
							<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
								<div className="grid grid-cols-12 gap-4 px-6 py-4 bg-gray-50 border-b border-gray-200">
									<div className="col-span-4 flex items-center gap-2">
										<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
											Maintenance Task
										</span>
										<ChevronDown className="w-4 h-4 text-purple-700" />
									</div>
									<div className="col-span-3">
										<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
											Tenant Unit
										</span>
									</div>
									<div className="col-span-3">
										<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
											Assigned Worker
										</span>
									</div>
									<div className="col-span-2">
										<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
											Status
										</span>
									</div>
								</div>
								<div className="divide-y divide-gray-200">
									{accumulatedRequests.map((request) => (
										<div
											key={request.id}
											onClick={() => setSelectedRequest(request)}
											className="grid grid-cols-12 gap-4 px-6 py-5 hover:bg-gray-50 transition-colors cursor-pointer"
										>
											<div className="col-span-4 flex items-center gap-4">
												<div className="w-16 h-16 rounded-lg flex-shrink-0 overflow-hidden flex items-center justify-center bg-purple-100">
													{request.imageUrl ? (
														<img
															src={request.imageUrl}
															alt={request.description}
															className="w-full h-full object-cover"
														/>
													) : issueIcons[request.issueType] ? (
														<img
															src={issueIcons[request.issueType]}
															alt={request.issueType}
															className="w-8 h-8"
														/>
													) : (
														<span className="text-2xl">🔧</span>
													)}
												</div>
												<div className="flex-1 min-w-0">
													<h3 className="font-semibold text-gray-900 truncate mb-1">
														{request.description}
													</h3>
													<p className="text-sm text-gray-500">By Tenant</p>
												</div>
											</div>
											<div className="col-span-3 flex items-center">
												<div className="flex items-center gap-3">
													<UserAvatar name={request.tenantName || "Unknown"} size="md" />
													<div className="min-w-0">
														<p className="text-sm font-medium text-gray-900 truncate">
															{request.tenantName || "Unknown"}
														</p>
														<p className="text-sm text-gray-500 truncate">
															{request.tenantUnit || request.propertyAddress}
														</p>
													</div>
												</div>
											</div>
											<div className="col-span-3 flex items-center">
												<p className="text-sm text-gray-900 truncate">
													{request.assignedWorkerName || "Unassigned"}
												</p>
											</div>
											<div className="col-span-2 flex items-center">
												<StatusBadge status={request.status} />
											</div>
										</div>
									))}
								</div>
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
			</PageContainer>

			{selectedRequest && (
				<MaintenanceDetailsModal
					request={selectedRequest}
					isOpen={!!selectedRequest}
					onClose={() => setSelectedRequest(null)}
					onSave={handleSaveStatus}
				/>
			)}
		</>
	);
}
