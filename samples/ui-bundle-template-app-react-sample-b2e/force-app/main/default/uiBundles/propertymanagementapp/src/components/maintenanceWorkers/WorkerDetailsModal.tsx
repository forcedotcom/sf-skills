import React from "react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogFooter,
} from "../ui/dialog";
import type { MaintenanceWorkerSearchNode } from "../../api/maintenanceWorkers/maintenanceWorkerSearchService";

interface WorkerDetailsModalProps {
	worker: MaintenanceWorkerSearchNode;
	isOpen: boolean;
	onClose: () => void;
}

export const WorkerDetailsModal: React.FC<WorkerDetailsModalProps> = ({
	worker,
	isOpen,
	onClose,
}) => {
	const name = worker.Name?.value ?? "\u2014";
	const organization = worker.Employment_Type__c?.value ?? worker.Type__c?.value ?? "\u2014";
	const phone = worker.Phone__c?.value ?? "\u2014";
	const isActive = worker.IsActive__c?.value;
	const status = typeof isActive === "boolean" ? (isActive ? "Active" : "Inactive") : "\u2014";

	return (
		<Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
			<DialogContent className="sm:max-w-md">
				<DialogHeader>
					<DialogTitle>Worker Details</DialogTitle>
				</DialogHeader>

				<div className="space-y-4">
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">
							Name
						</h3>
						<p className="text-base font-medium text-gray-900">{name}</p>
					</div>
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">
							Organization
						</h3>
						<p className="text-base text-gray-900">{organization}</p>
					</div>
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">
							Phone
						</h3>
						<p className="text-base text-gray-900">{phone}</p>
					</div>
					<div>
						<h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">
							Status
						</h3>
						<p className="text-base text-gray-900">{status}</p>
					</div>
				</div>

				<DialogFooter showCloseButton />
			</DialogContent>
		</Dialog>
	);
};
