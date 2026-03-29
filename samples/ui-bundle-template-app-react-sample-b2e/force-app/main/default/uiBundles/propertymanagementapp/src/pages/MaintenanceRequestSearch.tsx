import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "../components/ui/sonner";
import {
	searchMaintenanceRequests,
	fetchDistinctMaintenanceRequestStatus,
	fetchDistinctMaintenanceRequestType,
	fetchDistinctMaintenanceRequestPriority,
	type MaintenanceRequestSearchNode,
} from "../api/maintenanceRequests/maintenanceRequestSearchService";
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
import { MultiSelectFilter } from "../features/object-search/components/filters/MultiSelectFilter";
import { DateFilter } from "../features/object-search/components/filters/DateFilter";
import { ObjectSearchErrorState } from "../components/shared/ObjectSearchErrorState";
import PaginationControls from "../features/object-search/components/PaginationControls";
import { UserAvatar } from "../components/shared/UserAvatar";
import { Skeleton } from "../components/ui/skeleton";
import {
	Table,
	TableHeader,
	TableBody,
	TableRow,
	TableHead,
	TableCell,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Check } from "lucide-react";
import { MaintenanceDetailsModal } from "../components/maintenanceRequests/MaintenanceDetailsModal";
import { updateMaintenanceStatus } from "../api/maintenanceRequests/maintenanceRequests";
import PlumbingIcon from "../assets/icons/plumbing.svg";
import HVACIcon from "../assets/icons/hvac.svg";
import ElectricalIcon from "../assets/icons/electrical.svg";
import AppliancesIcon from "../assets/icons/appliances.svg";
import PestIcon from "../assets/icons/pest.svg";
import { PAGINATION_CONFIG } from "../lib/constants";
import type {
	Maintenance_Request__C_Filter,
	Maintenance_Request__C_OrderBy,
} from "../api/graphql-operations-types";
import { ResultOrder } from "../api/graphql-operations-types";
import { cn } from "../lib/utils";

const issueIcons: Record<string, string> = {
	Plumbing: PlumbingIcon,
	HVAC: HVACIcon,
	Electrical: ElectricalIcon,
	Appliance: AppliancesIcon,
	Pest: PestIcon,
};

const FILTER_CONFIGS: FilterFieldConfig[] = [
	{
		field: "search",
		label: "Search",
		type: "search",
		searchFields: ["Name"],
		placeholder: "Search by name...",
	},
	{ field: "Status__c", label: "Status", type: "picklist" },
	{ field: "Type__c", label: "Type", type: "picklist" },
	{ field: "Priority__c", label: "Priority", type: "picklist" },
	{ field: "Scheduled__c", label: "Scheduled", type: "datetime" },
];

const SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Subject" },
	{ field: "Status__c", label: "Status" },
	{ field: "Priority__c", label: "Priority" },
	{ field: "Scheduled__c", label: "Scheduled" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function MaintenanceRequestSearch() {
	const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequestSearchNode | null>(null);

	const { data: statusOptions } = useCachedAsyncData(fetchDistinctMaintenanceRequestStatus, [], {
		key: "distinctMaintenanceRequestStatus",
		ttl: 30_000,
	});
	const { data: typeOptions } = useCachedAsyncData(fetchDistinctMaintenanceRequestType, [], {
		key: "distinctMaintenanceRequestType",
		ttl: 30_000,
	});
	const { data: priorityOptions } = useCachedAsyncData(
		fetchDistinctMaintenanceRequestPriority,
		[],
		{ key: "distinctMaintenanceRequestPriority", ttl: 30_000 },
	);

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Maintenance_Request__C_Filter,
		Maintenance_Request__C_OrderBy
	>(FILTER_CONFIGS, SORT_CONFIGS, PAGINATION_CONFIG);
	const effectiveOrderBy = useMemo<Maintenance_Request__C_OrderBy>(
		() => query.orderBy ?? { CreatedDate: { order: ResultOrder.Desc } },
		[query.orderBy],
	);
	const searchKey = `maintenance-requests:${JSON.stringify({ where: query.where, orderBy: effectiveOrderBy, first: pagination.pageSize, after: pagination.afterCursor })}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchMaintenanceRequests({
				where: query.where,
				orderBy: effectiveOrderBy,
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, effectiveOrderBy, pagination.pageSize, pagination.afterCursor],
		{ key: searchKey },
	);

	const validMaintenanceRequestNodes = useMemo(
		() =>
			(data?.edges ?? []).reduce<MaintenanceRequestSearchNode[]>((acc, edge) => {
				if (edge?.node) acc.push(edge.node);
				return acc;
			}, []),
		[data?.edges],
	);

	const pageInfo = data?.pageInfo;
	const hasNextPage = pageInfo?.hasNextPage ?? false;
	const hasPreviousPage = pagination.pageIndex > 0;

	const handleSaveStatus = async (requestId: string, status: string) => {
		try {
			const success = await updateMaintenanceStatus(requestId, status);
			if (success) {
				if (selectedRequest?.Id === requestId) {
					setSelectedRequest({ ...selectedRequest, Status__c: { value: status } });
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

	return (
		<>
			<PageContainer>
				<PageHeader
					title="Maintenance Requests"
					description="Track and manage maintenance requests"
				/>
				<MaintenanceRequestSearchFilters
					filters={filters}
					statusOptions={statusOptions ?? []}
					typeOptions={typeOptions ?? []}
					priorityOptions={priorityOptions ?? []}
					resetAll={resetAll}
				/>

				<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
					<Table>
						<MaintenanceRequestSearchTableHeader />
						<TableBody>
							{loading && <MaintenanceRequestSearchSkeleton pageSize={pagination.pageSize} />}

							{!loading && error && <MaintenanceRequestSearchErrorState />}

							{!loading && !error && validMaintenanceRequestNodes.length === 0 && (
								<MaintenanceRequestSearchNoResults />
							)}

							{!loading && !error && validMaintenanceRequestNodes.length > 0 && (
								<MaintenanceRequestSearchTable
									requestNodes={validMaintenanceRequestNodes}
									setSelectedRequest={setSelectedRequest}
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

			{!loading && !error && selectedRequest && (
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

function MaintenanceRequestSearchFilters({
	filters,
	statusOptions,
	typeOptions,
	priorityOptions,
	resetAll,
}: {
	filters: UseObjectSearchParamsReturn<
		Maintenance_Request__C_Filter,
		Maintenance_Request__C_OrderBy
	>["filters"];
	statusOptions: Array<{ value: string; label: string }>;
	typeOptions: Array<{ value: string; label: string }>;
	priorityOptions: Array<{ value: string; label: string }>;
	resetAll: () => void;
}) {
	return (
		<FilterProvider
			filters={filters.active}
			onFilterChange={filters.set}
			onFilterRemove={filters.remove}
			onReset={resetAll}
		>
			<FilterRow ariaLabel="Maintenance Requests filters">
				<SearchFilter
					field="search"
					label="Search"
					placeholder="Search by name..."
					className="w-full sm:w-50"
				/>
				<MultiSelectFilter
					field="Status__c"
					label="Status"
					options={statusOptions}
					className="w-full sm:w-36"
				/>
				<MultiSelectFilter
					field="Type__c"
					label="Type"
					options={typeOptions}
					className="w-full sm:w-36"
				/>
				<MultiSelectFilter
					field="Priority__c"
					label="Priority"
					options={priorityOptions}
					className="w-full sm:w-36"
				/>
				<DateFilter
					field="Scheduled__c"
					label="Scheduled"
					filterType="datetime"
					className="w-full sm:w-56"
				/>
				<FilterResetButton />
			</FilterRow>
		</FilterProvider>
	);
}

function MaintenanceRequestSearchTableHeader() {
	return (
		<TableHeader>
			<TableRow>
				<TableHead className="w-4/12 max-w-xs px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Maintenance Task
				</TableHead>
				<TableHead className="w-3/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Tenant Unit
				</TableHead>
				<TableHead className="w-3/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Assigned Worker
				</TableHead>
				<TableHead className="w-2/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Status
				</TableHead>
			</TableRow>
		</TableHeader>
	);
}

function MaintenanceRequestSearchNoResults() {
	return (
		<TableRow>
			<TableCell colSpan={4} className="text-center py-12 text-gray-500">
				No maintenance requests found
			</TableCell>
		</TableRow>
	);
}

function MaintenanceRequestSearchTable({
	requestNodes,
	setSelectedRequest,
}: {
	requestNodes: MaintenanceRequestSearchNode[];
	setSelectedRequest: (request: MaintenanceRequestSearchNode) => void;
}) {
	return (
		<>
			{requestNodes.map((request) => {
				const issueType = request.Type__c?.value ?? "";
				const description = request.Description__c?.value ?? "";
				const tenantName = request.User__r?.Name?.value || "Unknown";
				const tenantUnit =
					request.Property__r?.Name?.value || request.Property__r?.Address__c?.value || "";
				const assignedWorkerName = request.Assigned_Worker__r?.Name?.value || "Unassigned";
				const status = request.Status__c?.value || "New";
				const imageVersionId =
					request.ContentDocumentLinks?.edges?.[0]?.node?.ContentDocument?.LatestPublishedVersionId
						?.value;
				const imageUrl = imageVersionId
					? `/sfc/servlet.shepherd/version/download/${imageVersionId}`
					: undefined;
				return (
					<TableRow
						key={request.Id}
						onClick={() => setSelectedRequest(request)}
						className="hover:bg-gray-50 transition-colors cursor-pointer"
					>
						<TableCell className="max-w-xs px-6 py-5">
							<div className="flex items-center gap-4">
								<div className="w-16 h-16 rounded-lg flex-shrink-0 overflow-hidden flex items-center justify-center bg-purple-100">
									{imageUrl ? (
										<img src={imageUrl} alt={description} className="w-full h-full object-cover" />
									) : issueIcons[issueType] ? (
										<img src={issueIcons[issueType]} alt={issueType} className="w-8 h-8" />
									) : (
										<span className="text-2xl">🔧</span>
									)}
								</div>
								<div className="flex-1 min-w-0">
									<h3 className="font-semibold text-gray-900 truncate mb-1">{description}</h3>
									<p className="text-sm text-gray-500">By Tenant</p>
								</div>
							</div>
						</TableCell>
						<TableCell className="px-6 py-5">
							<div className="flex items-center gap-3 min-w-0">
								<UserAvatar name={tenantName} size="md" />
								<div className="min-w-0 flex-1">
									<p className="font-medium text-gray-900 truncate">{tenantName}</p>
									<p className="text-gray-500 truncate">{tenantUnit}</p>
								</div>
							</div>
						</TableCell>
						<TableCell className="px-6 py-5">
							<p className="text-gray-900 truncate">{assignedWorkerName}</p>
						</TableCell>
						<TableCell className="px-6 py-5">
							<StatusBadge status={status} />
						</TableCell>
					</TableRow>
				);
			})}
		</>
	);
}

function StatusBadge({ status }: { status: string }) {
	const statusLower = status.toLowerCase();

	const style =
		statusLower === "new"
			? "bg-pink-100 text-pink-700"
			: statusLower === "in progress"
				? "bg-yellow-100 text-yellow-700"
				: statusLower === "resolved"
					? "bg-green-100 text-green-700"
					: "bg-gray-100 text-gray-700";

	const label =
		statusLower === "new"
			? "Needs Action"
			: statusLower === "in progress"
				? "In Progress"
				: statusLower === "resolved"
					? "Resolved"
					: status;

	return (
		<Badge className={cn("text-sm", style)}>
			{statusLower === "resolved" && <Check className="w-4 h-4" />}
			{(statusLower === "new" || statusLower === "in progress") && (
				<span className="w-2 h-2 rounded-full bg-current" />
			)}
			{label}
		</Badge>
	);
}

function MaintenanceRequestSearchSkeleton({ pageSize }: { pageSize: number }) {
	return (
		<>
			{Array.from({ length: pageSize }, (_, i) => (
				<TableRow key={i}>
					<TableCell className="px-6 py-5">
						<div className="flex items-center gap-4">
							<Skeleton className="h-16 w-16 rounded-lg shrink-0" />
							<div className="space-y-2 flex-1 min-w-0">
								<Skeleton className="h-4 w-full" />
								<Skeleton className="h-3 w-20" />
							</div>
						</div>
					</TableCell>
					<TableCell className="px-6 py-5">
						<div className="flex items-center gap-3">
							<Skeleton className="h-10 w-10 rounded-full shrink-0" />
							<div className="space-y-2 min-w-0">
								<Skeleton className="h-4 w-24" />
								<Skeleton className="h-3 w-32" />
							</div>
						</div>
					</TableCell>
					<TableCell className="px-6 py-5">
						<Skeleton className="h-4 w-28" />
					</TableCell>
					<TableCell className="px-6 py-5">
						<Skeleton className="h-6 w-20 rounded-full" />
					</TableCell>
				</TableRow>
			))}
		</>
	);
}

function MaintenanceRequestSearchErrorState() {
	const navigate = useNavigate();

	return (
		<TableRow>
			<TableCell colSpan={4} className="p-0">
				<ObjectSearchErrorState
					message="There was an error loading the maintenance requests. Please try again."
					onGoHome={() => navigate("/")}
					onRetry={() => navigate(0)}
				/>
			</TableCell>
		</TableRow>
	);
}
