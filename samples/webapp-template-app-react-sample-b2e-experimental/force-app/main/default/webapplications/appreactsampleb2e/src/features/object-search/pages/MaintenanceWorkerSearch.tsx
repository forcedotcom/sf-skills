import { useMemo, useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { toast } from "../../../components/ui/sonner";
import {
	searchMaintenanceWorkers,
	fetchDistinctMaintenanceWorkerType,
} from "../api/maintenanceWorkerSearchService";
import { useCachedAsyncData } from "../hooks/useCachedAsyncData";
import { useObjectSearchParams } from "../hooks/useObjectSearchParams";
import {
	useCursorBasedAccumulation,
	type CursorBasedData,
} from "../hooks/useCursorBasedAccumulation";
import type { FilterFieldConfig } from "../utils/filterUtils";
import type { SortFieldConfig } from "../utils/sortUtils";
import type { MaintenanceWorkerSearchResult } from "../api/maintenanceWorkerSearchService";
import type { PaginationConfig } from "../hooks/useObjectSearchParams";
import { getAllMaintenanceRequests } from "../../../api/maintenance";
import { PageHeader } from "../../../components/layout/PageHeader";
import { PageContainer } from "../../../components/layout/PageContainer";
import { ObjectSearchFilterRow } from "../components/ObjectSearchFilterRow";
import { ObjectSearchErrorState } from "../components/ObjectSearchErrorState";
import { ObjectSearchLoadingState } from "../components/ObjectSearchLoadingState";
import PaginationControls from "../components/PaginationControls";
import { Skeleton } from "../../../components/ui/skeleton";
import { nodeToMaintenanceWorker } from "../../../lib/maintenanceWorkerAdapter";
import type { MaintenanceWorker } from "../../../lib/types";

const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 12,
	validPageSizes: [6, 12, 24, 48],
};

type MaintenanceWorkerNode = NonNullable<
	NonNullable<NonNullable<MaintenanceWorkerSearchResult["edges"]>[number]>["node"]
>;

function buildFilterConfigs(
	typeOptions: Array<{ value: string; label: string }>,
): FilterFieldConfig[] {
	return [
		{
			field: "search",
			label: "Search",
			type: "search",
			searchFields: ["Name", "Location__c", "Phone__c"],
			placeholder: "Search by name, location, or phone...",
		},
		{ field: "Name", label: "Name", type: "text", placeholder: "Worker name..." },
		{
			field: "Employment_Type__c",
			label: "Employment Type",
			type: "picklist",
			options: typeOptions,
		},
		{ field: "Location__c", label: "Location", type: "text", placeholder: "Location" },
		{ field: "Hourly_Rate__c", label: "Hourly Rate", type: "numeric" },
		{ field: "CreatedDate", label: "Created Date", type: "date" },
	];
}

const SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Name" },
	{ field: "Employment_Type__c", label: "Employment Type" },
	{ field: "Hourly_Rate__c", label: "Hourly Rate" },
	{ field: "Rating__c", label: "Rating" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function MaintenanceWorkerSearch() {
	const navigate = useNavigate();
	const [selectedWorker, setSelectedWorker] = useState<MaintenanceWorker | null>(null);
	const [retryCount, setRetryCount] = useState(0);
	const [requestCountsLoading, setRequestCountsLoading] = useState(true);
	const [requestCounts, setRequestCounts] = useState<Record<string, number>>({});

	useEffect(() => {
		let mounted = true;
		async function fetchRequestCounts() {
			try {
				setRequestCountsLoading(true);
				const requests = await getAllMaintenanceRequests(500);
				if (!mounted) return;
				const counts: Record<string, number> = {};
				for (const req of requests) {
					if (req.status !== "Resolved" && req.assignedWorkerName) {
						const workerName = req.assignedWorkerName;
						counts[workerName] = (counts[workerName] || 0) + 1;
					}
				}
				setRequestCounts(counts);
			} catch (err) {
				console.error("Error fetching request counts:", err);
				toast.error("Could not load request counts", {
					description: "Request counts may be unavailable. You can still browse workers.",
				});
			} finally {
				if (mounted) setRequestCountsLoading(false);
			}
		}
		fetchRequestCounts();
		return () => {
			mounted = false;
		};
	}, []);

	const { data: typeOptions } = useCachedAsyncData(fetchDistinctMaintenanceWorkerType, [], {
		key: "distinctMaintenanceWorkerType",
		ttl: 300_000,
	});

	const filterConfigs = useMemo(() => buildFilterConfigs(typeOptions ?? []), [typeOptions]);

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Record<string, unknown>,
		Record<string, unknown>
	>(filterConfigs, SORT_CONFIGS, PAGINATION_CONFIG);

	const queryKey = useMemo(
		() => JSON.stringify({ where: query.where, orderBy: query.orderBy }),
		[query.where, query.orderBy],
	);

	const searchKey = `maintenance-workers:${JSON.stringify({ where: query.where, orderBy: query.orderBy, first: pagination.pageSize, after: pagination.afterCursor })}:${retryCount}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchMaintenanceWorkers({
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
	} = useCursorBasedAccumulation<MaintenanceWorkerNode>({
		data: data as CursorBasedData<MaintenanceWorkerNode> | undefined,
		loading,
		isFirstPage: !pagination.afterCursor,
		goToNextPage: pagination.goToNextPage,
		resetDeps: [queryKey],
	});

	const accumulatedWorkers = useMemo(() => {
		const base = accumulatedNodes.map((node) =>
			nodeToMaintenanceWorker(node as Record<string, unknown>),
		);
		return base.map((w) => ({
			...w,
			activeRequestsCount: requestCounts[w.name] ?? 0,
		}));
	}, [accumulatedNodes, requestCounts]);

	const filterRow = (
		<ObjectSearchFilterRow
			configs={filterConfigs}
			activeFilters={filters.active}
			onFilterChange={filters.set}
			onFilterRemove={filters.remove}
			onReset={resetAll}
			ariaLabel="Maintenance Workers filters"
		/>
	);

	if (error && accumulatedWorkers.length === 0) {
		return (
			<ObjectSearchErrorState
				title="Maintenance Workers"
				description="View and filter maintenance workers"
				filterRow={filterRow}
				message="There was an error loading the maintenance workers. Please try again."
				onGoHome={() => navigate("/")}
				onRetry={() => setRetryCount((c) => c + 1)}
			/>
		);
	}

	if ((loading || requestCountsLoading) && accumulatedWorkers.length === 0) {
		return (
			<ObjectSearchLoadingState
				title="Maintenance Workers"
				description="View and filter maintenance workers"
				filterRow={filterRow}
			>
				<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
					<div className="grid grid-cols-12 gap-4 px-6 py-4 bg-gray-50 border-b border-gray-200">
						<div className="col-span-5">
							<Skeleton className="h-4 w-16" />
						</div>
						<div className="col-span-4">
							<Skeleton className="h-4 w-24" />
						</div>
						<div className="col-span-2">
							<Skeleton className="h-4 w-28" />
						</div>
						<div className="col-span-1">
							<Skeleton className="h-4 w-14" />
						</div>
					</div>
					<div className="divide-y divide-gray-200">
						{Array.from({ length: pagination.pageSize }, (_, i) => (
							<div key={i} className="grid grid-cols-12 gap-4 px-6 py-4">
								<div className="col-span-5">
									<Skeleton className="h-4 w-32" />
								</div>
								<div className="col-span-4">
									<Skeleton className="h-4 w-24" />
								</div>
								<div className="col-span-2">
									<Skeleton className="h-4 w-12" />
								</div>
								<div className="col-span-1">
									<Skeleton className="h-4 w-16" />
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
			<PageHeader title="Maintenance Workers" description="View and filter maintenance workers" />

			<PageContainer>
				<div className="max-w-7xl mx-auto space-y-6">
					{filterRow}

					{accumulatedWorkers.length === 0 ? (
						<div className="text-center py-12 text-gray-500">No maintenance workers found</div>
					) : (
						<>
							<div className="overflow-x-auto rounded-lg shadow-sm border border-gray-200">
								<div className="min-w-[560px] bg-white">
									<div className="grid grid-cols-12 gap-4 px-6 py-4 bg-gray-50 border-b border-gray-200">
										<div className="col-span-5">
											<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
												Name
											</span>
										</div>
										<div className="col-span-4">
											<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
												Organization
											</span>
										</div>
										<div className="col-span-2">
											<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
												Active Requests
											</span>
										</div>
										<div className="col-span-1">
											<span className="text-sm font-semibold text-purple-700 uppercase tracking-wide">
												Status
											</span>
										</div>
									</div>
									<div className="divide-y divide-gray-200">
										{accumulatedWorkers.map((worker) => (
											<div
												key={worker.id}
												onClick={() => setSelectedWorker(worker)}
												className="grid grid-cols-12 gap-4 px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
											>
												<div className="col-span-5 font-medium text-gray-900 truncate">
													{worker.name}
												</div>
												<div className="col-span-4 text-gray-600 truncate">
													{worker.organization ?? "—"}
												</div>
												<div className="col-span-2 text-gray-600 truncate">
													{worker.activeRequestsCount ?? "—"}
												</div>
												<div className="col-span-1 text-gray-600 truncate">
													{worker.status ?? "—"}
												</div>
											</div>
										))}
									</div>
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

			{selectedWorker && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
					role="dialog"
					aria-modal="true"
					aria-labelledby="worker-dialog-title"
					onClick={() => setSelectedWorker(null)}
				>
					<div
						className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6"
						onClick={(e) => e.stopPropagation()}
					>
						<h2 id="worker-dialog-title" className="text-lg font-semibold text-gray-900 mb-4">
							Worker Details
						</h2>
						<dl className="space-y-2 text-sm">
							<div>
								<dt className="text-gray-500">Name</dt>
								<dd className="font-medium text-gray-900">{selectedWorker.name}</dd>
							</div>
							<div>
								<dt className="text-gray-500">Organization</dt>
								<dd className="text-gray-900">{selectedWorker.organization ?? "—"}</dd>
							</div>
							<div>
								<dt className="text-gray-500">Phone</dt>
								<dd className="text-gray-900">{selectedWorker.phone ?? "—"}</dd>
							</div>
							<div>
								<dt className="text-gray-500">Status</dt>
								<dd className="text-gray-900">{selectedWorker.status ?? "—"}</dd>
							</div>
						</dl>
						<div className="mt-6 flex justify-end">
							<button
								type="button"
								onClick={() => setSelectedWorker(null)}
								className="px-4 py-2 text-sm font-medium text-purple-700 hover:bg-purple-50 rounded-md"
							>
								Close
							</button>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
