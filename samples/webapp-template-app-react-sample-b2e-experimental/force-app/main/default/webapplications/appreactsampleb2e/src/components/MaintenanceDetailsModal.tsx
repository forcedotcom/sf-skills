import React, { useState } from "react";
import { X } from "lucide-react";
import { Button } from "./ui/button";
import { PriorityBadge } from "./PriorityBadge";
import type { MaintenanceRequest } from "../lib/types";

interface MaintenanceDetailsModalProps {
	request: MaintenanceRequest;
	isOpen: boolean;
	onClose: () => void;
	onSave: (requestId: string, status: string) => Promise<void>;
}

export const MaintenanceDetailsModal: React.FC<MaintenanceDetailsModalProps> = ({
	request,
	isOpen,
	onClose,
	onSave,
}) => {
	const [selectedStatus, setSelectedStatus] = useState(request.status);
	const [isSaving, setIsSaving] = useState(false);

	// Determine if status is editable
	// All statuses except Resolved can be edited
	const isStatusEditable = request.status !== "Resolved";

	// Status options - all possible statuses
	const statusOptions = ["New", "Assigned", "In Progress", "On Hold", "Resolved"];

	const handleSave = async () => {
		if (!isStatusEditable) return;

		setIsSaving(true);
		try {
			await onSave(request.id, selectedStatus);
			onClose();
		} catch (error) {
			console.error("Error saving status:", error);
		} finally {
			setIsSaving(false);
		}
	};

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center">
			{/* Backdrop */}
			<div className="fixed inset-0 bg-black/50" onClick={onClose} />

			{/* Modal */}
			<div className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
				{/* Header */}
				<div className="flex items-center justify-between p-6 border-b border-gray-200">
					<h2 className="text-xl font-semibold text-gray-900">Maintenance Request Details</h2>
					<button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
						<X className="w-6 h-6" />
					</button>
				</div>

				{/* Content */}
				<div className="p-6 space-y-6">
					{/* Image */}
					{request.imageUrl && (
						<div>
							<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Image
							</h3>
							<div className="w-full h-64 rounded-lg bg-gray-200 overflow-hidden">
								<img
									src={request.imageUrl}
									alt={request.description}
									className="w-full h-full object-cover"
								/>
							</div>
						</div>
					)}

					{/* Description */}
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
							Description
						</h3>
						<p className="text-lg font-medium text-gray-900">{request.description}</p>
					</div>

					{/* Two Column Layout */}
					<div className="grid grid-cols-2 gap-6">
						{/* Left Column */}
						<div className="space-y-6">
							{/* Issue Type */}
							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Issue Type
								</h3>
								<p className="text-base text-gray-900">{request.issueType}</p>
							</div>

							{/* Property */}
							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Property
								</h3>
								<p className="text-base text-gray-900">{request.propertyAddress}</p>
							</div>

							{/* Tenant */}
							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Tenant
								</h3>
								<p className="text-base text-gray-900">{request.tenantName || "Unknown"}</p>
								{request.tenantUnit && (
									<p className="text-sm text-gray-600 mt-1">Unit: {request.tenantUnit}</p>
								)}
							</div>

							{/* Scheduled Date */}
							{request.formattedDate && (
								<div>
									<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
										Scheduled Date
									</h3>
									<p className="text-base text-gray-900">{request.formattedDate}</p>
								</div>
							)}
						</div>

						{/* Right Column */}
						<div className="space-y-6">
							{/* Priority */}
							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Priority
								</h3>
								<PriorityBadge priority={request.priority} />
							</div>

							{/* Assigned Worker */}
							{request.assignedWorkerName && (
								<div>
									<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
										Assigned Worker
									</h3>
									<p className="text-base text-gray-900">{request.assignedWorkerName}</p>
									{request.assignedWorkerOrg && (
										<p className="text-sm text-gray-600 mt-1">{request.assignedWorkerOrg}</p>
									)}
								</div>
							)}
						</div>
					</div>

					{/* Status - Full Width */}
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
							Status
						</h3>
						{isStatusEditable ? (
							<select
								value={selectedStatus}
								onChange={(e) => setSelectedStatus(e.target.value)}
								className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							>
								{statusOptions.map((status) => (
									<option key={status} value={status}>
										{status}
									</option>
								))}
							</select>
						) : (
							<div className="flex items-center">
								<span className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md font-medium">
									{request.status}
								</span>
								<span className="ml-3 text-sm text-gray-500">(Cannot be modified)</span>
							</div>
						)}
					</div>
				</div>

				{/* Footer */}
				<div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
					<Button variant="outline" onClick={onClose} disabled={isSaving}>
						Close
					</Button>
					{isStatusEditable && (
						<Button
							onClick={handleSave}
							disabled={isSaving || selectedStatus === request.status}
							className="bg-purple-600 hover:bg-purple-700"
						>
							{isSaving ? "Saving..." : "Save Changes"}
						</Button>
					)}
				</div>
			</div>
		</div>
	);
};
