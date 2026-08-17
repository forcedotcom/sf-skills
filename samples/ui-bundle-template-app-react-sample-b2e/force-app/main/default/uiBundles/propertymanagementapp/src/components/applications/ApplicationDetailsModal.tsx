import React, { useState } from "react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogFooter,
} from "../ui/dialog";
import { Button } from "../ui/button";
import type { ApplicationSearchNode } from "../../api/applications/applicationSearchService";

interface ApplicationDetailsModalProps {
	application: ApplicationSearchNode;
	isOpen: boolean;
	onClose: () => void;
	onSave: (applicationId: string, status: string) => Promise<void>;
}

export const ApplicationDetailsModal: React.FC<ApplicationDetailsModalProps> = ({
	application,
	isOpen,
	onClose,
	onSave,
}) => {
	const status = application.Status__c?.value || "Unknown";
	const [selectedStatus, setSelectedStatus] = useState(status);
	const [isSaving, setIsSaving] = useState(false);

	const isStatusEditable =
		status.toLowerCase() !== "approved" && status.toLowerCase() !== "rejected";

	const statusOptions = ["Submitted", "Background Check", "Under Review", "Approved", "Rejected"];

	const handleSave = async () => {
		if (!isStatusEditable) return;

		setIsSaving(true);
		try {
			await onSave(application.Id, selectedStatus);
			onClose();
		} catch (error) {
			console.error("Error saving status:", error);
		} finally {
			setIsSaving(false);
		}
	};

	const applicantName = application.User__r?.Name?.value || "Unknown";
	const propertyName = application.Property__r?.Name?.value;
	const propertyAddress = application.Property__r?.Address__c?.value || "";
	const employment = application.Employment__c?.value;
	const references = application.References__c?.value;

	return (
		<Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
			<DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle>Application Details</DialogTitle>
				</DialogHeader>

				<div className="space-y-6">
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
							Applicant
						</h3>
						<p className="text-lg font-medium text-gray-900">{applicantName}</p>
					</div>

					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
							Property
						</h3>
						<p className="text-base text-gray-900">
							{propertyName && <span className="font-medium">{propertyName}</span>}
						</p>
						<p className="text-sm text-gray-600">{propertyAddress}</p>
					</div>

					{employment && (
						<div>
							<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Employment
							</h3>
							<p className="text-sm text-gray-700 whitespace-pre-wrap">{employment}</p>
						</div>
					)}

					{references && (
						<div>
							<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								References
							</h3>
							<p className="text-sm text-gray-700 whitespace-pre-wrap">{references}</p>
						</div>
					)}

					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
							Status
						</h3>
						{isStatusEditable ? (
							<select
								value={selectedStatus}
								onChange={(e) => setSelectedStatus(e.target.value)}
								aria-label="Application status"
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
