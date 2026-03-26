import React, { useState } from "react";
import { X } from "lucide-react";
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

	if (!isOpen) return null;

	const applicantName = application.User__r?.Name?.value || "Unknown";
	const propertyName = application.Property__r?.Name?.value;
	const propertyAddress = application.Property__r?.Address__c?.value || "";
	const employment = application.Employment__c?.value;
	const references = application.References__c?.value;

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center">
			<div className="fixed inset-0 bg-black/50" onClick={onClose} />

			<div className="relative bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
				<div className="flex items-center justify-between p-6 border-b border-gray-200">
					<h2 className="text-xl font-semibold text-gray-900">Application Details</h2>
					<button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
						<X className="w-6 h-6" />
					</button>
				</div>

				<div className="p-6 space-y-6">
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
