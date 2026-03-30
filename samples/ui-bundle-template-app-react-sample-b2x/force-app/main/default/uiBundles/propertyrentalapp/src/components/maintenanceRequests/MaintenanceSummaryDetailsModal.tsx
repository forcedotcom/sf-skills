/**
 * Read-only maintenance details for B2C Maintenance page (summary rows from maintenanceRequestApi).
 */
import { useEffect } from "react";
import { X } from "lucide-react";
import { StatusBadge } from "@/components/maintenanceRequests/StatusBadge";
import type { MaintenanceRequestNode } from "@/api/maintenanceRequests/maintenanceRequestApi";

export interface MaintenanceSummaryDetailsModalProps {
	request: MaintenanceRequestNode;
	onClose: () => void;
}

function formatDate(value: string | null): string {
	if (!value?.trim()) return "—";
	try {
		const d = new Date(value);
		return d.toLocaleDateString("en-US", {
			month: "short",
			day: "numeric",
			year: "numeric",
			hour: "numeric",
			minute: "2-digit",
			hour12: true,
		});
	} catch {
		return value;
	}
}

export default function MaintenanceSummaryDetailsModal({
	request,
	onClose,
}: MaintenanceSummaryDetailsModalProps) {
	useEffect(() => {
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		document.addEventListener("keydown", handleEscape);
		return () => document.removeEventListener("keydown", handleEscape);
	}, [onClose]);

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center p-4">
			<div className="fixed inset-0 bg-black/50" onClick={onClose} aria-hidden />
			<div
				role="dialog"
				aria-modal
				className="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white shadow-xl"
			>
				<div className="flex items-center justify-between border-b p-4">
					<h2 className="text-lg font-semibold">
						{request.Description__c?.value ?? request.Name?.value ?? "Request"}
					</h2>
					<button type="button" onClick={onClose} className="text-gray-500 hover:text-gray-800">
						<X className="h-5 w-5" />
					</button>
				</div>
				<div className="space-y-3 p-4 text-sm">
					{request.Description__c?.value && (
						<p className="text-gray-700">{request.Description__c.value}</p>
					)}
					<div className="flex flex-wrap gap-2">
						{request.Type__c?.value && (
							<span className="rounded bg-gray-100 px-2 py-0.5">{request.Type__c.value}</span>
						)}
						{request.Priority__c?.value && (
							<span className="rounded bg-gray-100 px-2 py-0.5">{request.Priority__c.value}</span>
						)}
						{request.Status__c?.value && <StatusBadge status={request.Status__c.value} />}
					</div>
					{request.Property__r?.Address__c?.value && (
						<p>
							<span className="font-medium">Property:</span> {request.Property__r.Address__c.value}
						</p>
					)}
					{request.User__r?.Name?.value && (
						<p>
							<span className="font-medium">Tenant:</span> {request.User__r.Name.value}
						</p>
					)}
					{request.Scheduled__c?.value && (
						<p>
							<span className="font-medium">Requested:</span>{" "}
							{formatDate(request.Scheduled__c.value)}
						</p>
					)}
				</div>
			</div>
		</div>
	);
}
