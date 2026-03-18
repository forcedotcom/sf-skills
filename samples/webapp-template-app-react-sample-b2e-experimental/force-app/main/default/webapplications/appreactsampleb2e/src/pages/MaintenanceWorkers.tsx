import { useState, useEffect, useMemo } from "react";
import { useListPage } from "../hooks/useListPage";
import { maintenanceWorkersListConfig } from "../lib/listPageConfig";
import { ListPageWithFilters } from "../components/list/ListPageWithFilters";
import { PageHeader } from "../components/layout/PageHeader";
import { getAllMaintenanceRequests } from "../api/maintenance";
import type { MaintenanceWorker } from "../lib/types";

export default function MaintenanceWorkers() {
	const list = useListPage(maintenanceWorkersListConfig);
	const [selectedWorker, setSelectedWorker] = useState<MaintenanceWorker | null>(null);
	const [requestCountsLoading, setRequestCountsLoading] = useState(true);
	const [requestCounts, setRequestCounts] = useState<Record<string, number>>({});

	// Fetch maintenance requests to calculate active request counts per worker
	useEffect(() => {
		let mounted = true;
		async function fetchRequestCounts() {
			try {
				setRequestCountsLoading(true);
				const requests = await getAllMaintenanceRequests(500);
				if (!mounted) return;

				// Count active requests (not "Resolved") per worker
				const counts: Record<string, number> = {};
				for (const req of requests) {
					if (req.status !== "Resolved" && req.assignedWorkerName) {
						const workerName = req.assignedWorkerName;
						counts[workerName] = (counts[workerName] || 0) + 1;
					}
				}
				setRequestCounts(counts);
			} catch (error) {
				console.error("Error fetching request counts:", error);
			} finally {
				if (mounted) setRequestCountsLoading(false);
			}
		}
		fetchRequestCounts();
		return () => {
			mounted = false;
		};
	}, []);

	// Enrich workers with active request counts
	const enrichedWorkers = useMemo(() => {
		return list.items.map((worker) => ({
			...worker,
			activeRequestsCount: requestCounts[worker.name] || 0,
		}));
	}, [list.items, requestCounts]);

	return (
		<>
			<PageHeader title="Maintenance Workers" description="View and filter maintenance workers" />

			<ListPageWithFilters
				filterProps={{
					filters: list.filters,
					picklistValues: list.picklistValues,
					formValues: list.formValues,
					onFormValueChange: list.onFormValueChange,
					onApply: list.onApplyFilters,
					onReset: list.onResetFilters,
					ariaLabel: maintenanceWorkersListConfig.filtersAriaLabel,
				}}
				filterError={list.filterError}
				loading={list.loading || requestCountsLoading}
				error={list.error}
				loadingMessage={maintenanceWorkersListConfig.loadingMessage}
				isEmpty={enrichedWorkers.length === 0}
				searchPlaceholder="Search by name, organization, status..."
				searchAriaLabel="Search workers"
			>
				<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
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
						{enrichedWorkers.length === 0 ? (
							<div className="text-center py-12 text-gray-500">No maintenance workers found</div>
						) : (
							enrichedWorkers.map((worker) => (
								<div
									key={worker.id}
									onClick={() => setSelectedWorker(worker)}
									className="grid grid-cols-12 gap-4 px-6 py-4 hover:bg-gray-50 transition-colors cursor-pointer"
								>
									<div className="col-span-5 font-medium text-gray-900">{worker.name}</div>
									<div className="col-span-4 text-gray-600">{worker.organization ?? "—"}</div>
									<div className="col-span-2 text-gray-600">
										{worker.activeRequestsCount ?? "—"}
									</div>
									<div className="col-span-1 text-gray-600">{worker.status ?? "—"}</div>
								</div>
							))
						)}
					</div>
				</div>
				{list.canLoadMore && (
					<div className="flex justify-center mt-6">
						<button
							type="button"
							onClick={list.onLoadMore}
							disabled={list.loadMoreLoading}
							className="px-6 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-lg text-sm font-medium disabled:opacity-50"
						>
							{list.loadMoreLoading ? "Loading..." : "Load More"}
						</button>
					</div>
				)}
			</ListPageWithFilters>
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
