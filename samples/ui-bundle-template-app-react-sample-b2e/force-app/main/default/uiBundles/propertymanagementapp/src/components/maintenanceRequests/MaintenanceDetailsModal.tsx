import React, { useState } from "react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogFooter,
} from "../ui/dialog";
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

	const description = request.Description__c?.value || "";
	const issueType = request.Type__c?.value || "General";
	const propertyAddress = request.Property__r?.Address__c?.value || "Unknown Address";
	const tenantName = request.User__r?.Name?.value || "Unknown";
	const tenantUnit = request.Property__r?.Name?.value || request.Property__r?.Address__c?.value;
	const formattedDate = formatScheduledDate(request.Scheduled__c?.value);
	const priority = request.Priority__c?.value;

	return (
		<Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
			<DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle>Maintenance Request Details</DialogTitle>
				</DialogHeader>

				<div className="space-y-6">
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
								aria-label="Maintenance request status"
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

				<DialogFooter>
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
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
};

type Priority = "Emergency" | "High" | "Standard";

const priorityStyles: Record<Priority, string> = {
	Emergency: "bg-red-100 text-red-700 border-red-200 text-sm",
	High: "bg-orange-100 text-orange-700 border-orange-200 text-sm",
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
