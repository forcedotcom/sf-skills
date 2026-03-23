import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "../../../components/ui/sonner";
import {
	searchApplications,
	fetchDistinctApplicationStatus,
} from "../api/applicationSearchService";
import { useCachedAsyncData } from "../hooks/useCachedAsyncData";
import { useObjectSearchParams } from "../hooks/useObjectSearchParams";
import {
	useCursorBasedAccumulation,
	type CursorBasedData,
} from "../hooks/useCursorBasedAccumulation";
import type { FilterFieldConfig } from "../utils/filterUtils";
import type { SortFieldConfig } from "../utils/sortUtils";
import type { ApplicationSearchResult } from "../api/applicationSearchService";
import type { PaginationConfig } from "../hooks/useObjectSearchParams";
import { PageHeader } from "../../../components/layout/PageHeader";
import { PageContainer } from "../../../components/layout/PageContainer";
import { ObjectSearchFilterRow } from "../components/ObjectSearchFilterRow";
import { ObjectSearchErrorState } from "../components/ObjectSearchErrorState";
import { ObjectSearchLoadingState } from "../components/ObjectSearchLoadingState";
import PaginationControls from "../components/PaginationControls";
import { ApplicationsTable } from "../../../components/ApplicationsTable";
import { ApplicationDetailsModal } from "../../../components/ApplicationDetailsModal";
import { Skeleton } from "../../../components/ui/skeleton";
import { nodeToApplication } from "../../../lib/applicationAdapter";
import { updateApplicationStatus } from "../../../api/applications";
import type { Application } from "../../../lib/types";

const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 12,
	validPageSizes: [6, 12, 24, 48],
};

type ApplicationNode = NonNullable<
	NonNullable<NonNullable<ApplicationSearchResult["edges"]>[number]>["node"]
>;

function buildFilterConfigs(
	statusOptions: Array<{ value: string; label: string }>,
): FilterFieldConfig[] {
	return [
		{
			field: "search",
			label: "Search",
			type: "search",
			searchFields: ["Name"],
			placeholder: "Search by name or application details...",
		},
		{ field: "Status__c", label: "Status", type: "picklist", options: statusOptions },
		{ field: "Start_Date__c", label: "Start Date", type: "date" },
		{ field: "CreatedDate", label: "Created Date", type: "date" },
	];
}

const SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Application" },
	{ field: "Status__c", label: "Status" },
	{ field: "Start_Date__c", label: "Start Date" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function ApplicationSearch() {
	const navigate = useNavigate();
	const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);
	const [retryCount, setRetryCount] = useState(0);

	const { data: statusOptions } = useCachedAsyncData(fetchDistinctApplicationStatus, [], {
		key: "distinctApplicationStatus",
		ttl: 300_000,
	});

	const filterConfigs = useMemo(() => buildFilterConfigs(statusOptions ?? []), [statusOptions]);

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Record<string, unknown>,
		Record<string, unknown>
	>(filterConfigs, SORT_CONFIGS, PAGINATION_CONFIG);

	const queryKey = useMemo(
		() => JSON.stringify({ where: query.where, orderBy: query.orderBy }),
		[query.where, query.orderBy],
	);

	const searchKey = `applications:${JSON.stringify({ where: query.where, orderBy: query.orderBy, first: pagination.pageSize, after: pagination.afterCursor })}:${retryCount}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchApplications({
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
	} = useCursorBasedAccumulation<ApplicationNode>({
		data: data as CursorBasedData<ApplicationNode> | undefined,
		loading,
		isFirstPage: !pagination.afterCursor,
		goToNextPage: pagination.goToNextPage,
		resetDeps: [queryKey],
	});

	const accumulatedApplications = useMemo(
		() => accumulatedNodes.map((node) => nodeToApplication(node as Record<string, unknown>)),
		[accumulatedNodes],
	);

	const handleSaveStatus = async (applicationId: string, status: string) => {
		try {
			const success = await updateApplicationStatus(applicationId, status);
			if (success) {
				if (selectedApplication?.id === applicationId) {
					setSelectedApplication({ ...selectedApplication, status });
				}
				toast.success("Status updated", {
					description: "Application status has been updated successfully.",
				});
			} else {
				toast.error("Update failed", {
					description: "Failed to update application status. Please try again.",
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
			ariaLabel="Applications filters"
		/>
	);

	if (error && accumulatedApplications.length === 0) {
		return (
			<ObjectSearchErrorState
				title="Applications"
				description="Manage and review rental applications"
				filterRow={filterRow}
				message="There was an error loading the applications. Please try again."
				onGoHome={() => navigate("/")}
				onRetry={() => setRetryCount((c) => c + 1)}
			/>
		);
	}

	if (loading && accumulatedApplications.length === 0) {
		return (
			<ObjectSearchLoadingState
				title="Applications"
				description="Manage and review rental applications"
				filterRow={filterRow}
			>
				<div className="border border-gray-200 rounded-lg shadow-sm overflow-x-auto bg-white">
					<table className="w-full">
						<thead className="bg-gray-50 border-b border-gray-200">
							<tr>
								<th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
									User
								</th>
								<th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
									Start Date
								</th>
								<th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
									Status
								</th>
							</tr>
						</thead>
						<tbody className="bg-white divide-y divide-gray-200">
							{Array.from({ length: pagination.pageSize }, (_, i) => (
								<tr key={i}>
									<td className="px-6 py-4 whitespace-nowrap">
										<div className="flex items-center">
											<Skeleton className="h-10 w-10 rounded-full shrink-0" />
											<div className="ml-4 space-y-2">
												<Skeleton className="h-4 w-32" />
												<Skeleton className="h-3 w-48" />
											</div>
										</div>
									</td>
									<td className="px-6 py-4 whitespace-nowrap">
										<Skeleton className="h-4 w-24" />
									</td>
									<td className="px-6 py-4 whitespace-nowrap">
										<Skeleton className="h-6 w-20 rounded-full" />
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</ObjectSearchLoadingState>
		);
	}

	return (
		<>
			<PageHeader title="Applications" description="Manage and review rental applications" />

			<PageContainer>
				<div className="max-w-7xl mx-auto space-y-6">
					{filterRow}

					<ApplicationsTable
						applications={accumulatedApplications}
						onRowClick={setSelectedApplication}
					/>

					{accumulatedApplications.length > 0 && (
						<PaginationControls
							variant="loadMore"
							pageSize={pagination.pageSize}
							pageSizeOptions={PAGINATION_CONFIG.validPageSizes}
							onPageSizeChange={pagination.setPageSize}
							hasNextPage={hasNextPage}
							onLoadMore={onLoadMore}
							loadMoreLoading={loadMoreLoading}
						/>
					)}
				</div>
			</PageContainer>

			{selectedApplication && (
				<ApplicationDetailsModal
					application={selectedApplication}
					isOpen={!!selectedApplication}
					onClose={() => setSelectedApplication(null)}
					onSave={handleSaveStatus}
				/>
			)}
		</>
	);
}
