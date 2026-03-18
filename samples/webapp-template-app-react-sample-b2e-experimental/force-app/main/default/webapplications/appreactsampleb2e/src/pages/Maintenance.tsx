import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useListPage } from "../hooks/useListPage";
import { maintenanceRequestsListConfig } from "../lib/listPageConfig";
import { ListPageWithFilters } from "../components/list/ListPageWithFilters";
import { PageHeader } from "../components/layout/PageHeader";
import { UserAvatar } from "../components/UserAvatar";
import { StatusBadge } from "../components/StatusBadge";
import { MaintenanceDetailsModal } from "../components/MaintenanceDetailsModal";
import { updateMaintenanceStatus } from "../api/maintenance";
import type { MaintenanceRequest } from "../lib/types";
import PlumbingIcon from "../assets/icons/plumbing.svg";
import HVACIcon from "../assets/icons/hvac.svg";
import ElectricalIcon from "../assets/icons/electrical.svg";
import AppliancesIcon from "../assets/icons/appliances.svg";
import PestIcon from "../assets/icons/pest.svg";

const issueIcons: Record<string, string> = {
	Plumbing: PlumbingIcon,
	HVAC: HVACIcon,
	Electrical: ElectricalIcon,
	Appliance: AppliancesIcon,
	Pest: PestIcon,
};

export default function Maintenance() {
	const list = useListPage(maintenanceRequestsListConfig);
	const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequest | null>(null);
	const [notification, setNotification] = useState<{
		message: string;
		type: "success" | "error";
	} | null>(null);

	useEffect(() => {
		if (notification) {
			const timer = setTimeout(() => setNotification(null), 5000);
			return () => clearTimeout(timer);
		}
	}, [notification]);

	const handleRowClick = (request: MaintenanceRequest) => {
		setSelectedRequest(request);
	};

	const handleCloseModal = () => {
		setSelectedRequest(null);
	};

	const handleSaveStatus = async (requestId: string, status: string) => {
		try {
			const success = await updateMaintenanceStatus(requestId, status);
			if (success) {
				if (selectedRequest?.id === requestId) {
					setSelectedRequest({ ...selectedRequest, status });
				}
				setNotification({
					message: "Maintenance request status updated successfully!",
					type: "success",
				});
			} else {
				setNotification({ message: "Failed to update maintenance request status", type: "error" });
			}
		} catch (error) {
			console.error("Error updating maintenance request:", error);
			setNotification({ message: "An error occurred while updating the status", type: "error" });
		}
	};

	return (
		<>
			{notification && (
				<div className="fixed top-4 right-4 z-50 animate-slide-in">
					<div
						className={`px-6 py-4 rounded-lg shadow-lg ${
							notification.type === "success" ? "bg-green-500 text-white" : "bg-red-500 text-white"
						}`}
					>
						<div className="flex items-center gap-3">
							<span className="text-lg">{notification.type === "success" ? "✓" : "✕"}</span>
							<p className="font-medium">{notification.message}</p>
						</div>
					</div>
				</div>
			)}

			<PageHeader
				title="Maintenance Requests"
				description="Track and manage maintenance requests"
			/>

			<ListPageWithFilters
				filterProps={{
					filters: list.filters,
					picklistValues: list.picklistValues,
					formValues: list.formValues,
					onFormValueChange: list.onFormValueChange,
					onApply: list.onApplyFilters,
					onReset: list.onResetFilters,
					ariaLabel: maintenanceRequestsListConfig.filtersAriaLabel,
				}}
				filterError={list.filterError}
				loading={list.loading}
				error={list.error}
				loadingMessage={maintenanceRequestsListConfig.loadingMessage}
				isEmpty={list.items.length === 0}
				searchPlaceholder="Search by description, tenant, property, status..."
				searchAriaLabel="Search maintenance requests"
			>
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
						{list.items.length === 0 ? (
							<div className="text-center py-12 text-gray-500">No maintenance requests found</div>
						) : (
							list.items.map((request) => (
								<div
									key={request.id}
									onClick={() => handleRowClick(request)}
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

			{selectedRequest && (
				<MaintenanceDetailsModal
					request={selectedRequest}
					isOpen={!!selectedRequest}
					onClose={handleCloseModal}
					onSave={handleSaveStatus}
				/>
			)}
		</>
	);
}
