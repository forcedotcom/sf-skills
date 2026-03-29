import React, { useState } from "react";
import { X } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import type { MaintenanceRequestSearchNode } from "../../api/maintenanceRequests/maintenanceRequestSearchService";

interface MaintenanceDetailsModalProps {
	request: MaintenanceRequestSearchNode;
	isOpen: boolean;
	onClose: () => void;
	onSave: (requestId: string, status: string) => Promise<void>;
}

function formatScheduledDate(dateValue: string | null | undefined): string | undefined {
	if (!dateValue) return undefined;
	const date = new Date(dateValue);
	return date.toLocaleString(undefined, {
		month: "short",
		day: "numeric",
		hour: "numeric",
		minute: "2-digit",
	});
}

export const MaintenanceDetailsModal: React.FC<MaintenanceDetailsModalProps> = ({
	request,
	isOpen,
	onClose,
	onSave,
}) => {
	const status = request.Status__c?.value || "New";
	const [selectedStatus, setSelectedStatus] = useState(status);
	const [isSaving, setIsSaving] = useState(false);

	// Determine if status is editable
	// All statuses except Resolved can be edited
	const isStatusEditable = status !== "Resolved";

	// Status options - all possible statuses
	const statusOptions = ["New", "Assigned", "In Progress", "On Hold", "Resolved"];

	const handleSave = async () => {
		if (!isStatusEditable) return;

		setIsSaving(true);
		try {
			await onSave(request.Id, selectedStatus);
			onClose();
		} catch (error) {
			console.error("Error saving status:", error);
		} finally {
			setIsSaving(false);
		}
	};

	if (!isOpen) return null;

	const description = request.Description__c?.value || "";
	const issueType = request.Type__c?.value || "General";
	const propertyAddress = request.Property__r?.Address__c?.value || "Unknown Address";
	const tenantName = request.User__r?.Name?.value || "Unknown";
	const tenantUnit = request.Property__r?.Name?.value || request.Property__r?.Address__c?.value;
	const formattedDate = formatScheduledDate(request.Scheduled__c?.value);
	const priority = request.Priority__c?.value;

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center">
			<div className="fixed inset-0 bg-black/50" onClick={onClose} />

			<div className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
				<div className="flex items-center justify-between p-6 border-b border-gray-200">
					<h2 className="text-xl font-semibold text-gray-900">Maintenance Request Details</h2>
					<button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
						<X className="w-6 h-6" />
					</button>
				</div>

				<div className="p-6 space-y-6">
					{/* Description */}
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
							Description
						</h3>
						<p className="text-lg font-medium text-gray-900">{description}</p>
					</div>

					<div className="grid grid-cols-2 gap-6">
						<div className="space-y-6">
							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Issue Type
								</h3>
								<p className="text-base text-gray-900">{issueType}</p>
							</div>

							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Property
								</h3>
								<p className="text-base text-gray-900">{propertyAddress}</p>
							</div>

							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Tenant
								</h3>
								<p className="text-base text-gray-900">{tenantName}</p>
								{tenantUnit && <p className="text-sm text-gray-600 mt-1">Unit: {tenantUnit}</p>}
							</div>

							{formattedDate && (
								<div>
									<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
										Scheduled Date
									</h3>
									<p className="text-base text-gray-900">{formattedDate}</p>
								</div>
							)}
						</div>

						<div className="space-y-6">
							<div>
								<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
									Priority
								</h3>
								<PriorityBadge priority={priority} />
							</div>
						</div>
					</div>

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
								{statusOptions.map((s) => (
									<option key={s} value={s}>
										{s}
									</option>
								))}
							</select>
						) : (
							<div className="flex items-center">
								<span className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md font-medium">
									{status}
								</span>
								<span className="ml-3 text-sm text-gray-500">(Cannot be modified)</span>
							</div>
						)}
					</div>
				</div>

				<div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
					<Button variant="outline" onClick={onClose} disabled={isSaving}>
						Close
					</Button>
					{isStatusEditable && (
						<Button
							onClick={handleSave}
							disabled={isSaving || selectedStatus === status}
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

type Priority = "Emergency (2hr)" | "High (Same Day)" | "Standard";

const priorityStyles: Record<Priority, string> = {
	"Emergency (2hr)": "bg-red-100 text-red-700 border-red-200 text-sm",
	"High (Same Day)": "bg-orange-100 text-orange-700 border-orange-200 text-sm",
	Standard: "bg-blue-100 text-blue-700 border-blue-200 text-sm",
};

const PriorityBadge: React.FC<{ priority: string | null | undefined }> = ({ priority }) => {
	return (
		<Badge
			className={`border ${priority && priority in priorityStyles ? priorityStyles[priority as Priority] : priorityStyles.Standard}`}
		>
			{priority && priority in priorityStyles ? priority : "Standard"}
		</Badge>
	);
};
