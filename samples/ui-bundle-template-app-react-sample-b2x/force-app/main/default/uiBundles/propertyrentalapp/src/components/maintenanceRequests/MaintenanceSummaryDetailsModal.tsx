/**
 * Read-only maintenance details for B2C Maintenance page (summary rows from maintenanceRequestApi).
 */
import { useCallback, useEffect, useRef } from "react";
import { X } from "lucide-react";
import { StatusBadge } from "@/components/maintenanceRequests/StatusBadge";
import type { MaintenanceRequestNode } from "@/api/maintenanceRequests/maintenanceRequestApi";

export interface MaintenanceSummaryDetailsModalProps {
	request: MaintenanceRequestNode;
	onClose: () => void;
}

const TITLE_ID = "maintenance-summary-details-title";

const FOCUSABLE_SELECTOR =
	'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

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
	const dialogRef = useRef<HTMLDivElement>(null);
	const closeButtonRef = useRef<HTMLButtonElement>(null);

	// Move focus into the dialog on open and return it to the invoking element on close.
	useEffect(() => {
		const previouslyFocused = document.activeElement as HTMLElement | null;
		closeButtonRef.current?.focus();
		return () => previouslyFocused?.focus?.();
	}, []);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLDivElement>) => {
			if (e.key === "Escape") {
				onClose();
				return;
			}
			if (e.key !== "Tab") return;

			// Trap Tab within the dialog (WCAG 2.4.3 / 2.1.2 for modal content).
			const focusable = Array.from(
				dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR) ?? [],
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			const active = document.activeElement;
			if (e.shiftKey && (active === first || !dialogRef.current?.contains(active))) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && active === last) {
				e.preventDefault();
				first.focus();
			}
		},
		[onClose],
	);

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center p-4">
			<div className="fixed inset-0 bg-black/50" onClick={onClose} aria-hidden />
			<div
				ref={dialogRef}
				role="dialog"
				aria-modal="true"
				aria-labelledby={TITLE_ID}
				onKeyDown={handleKeyDown}
				className="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-white shadow-xl"
			>
				<div className="flex items-center justify-between border-b p-4">
					<h2 id={TITLE_ID} className="text-lg font-semibold">
						{request.Description__c?.value ?? request.Name?.value ?? "Request"}
					</h2>
					<button
						ref={closeButtonRef}
						type="button"
						onClick={onClose}
						aria-label="Close dialog"
						className="text-gray-500 hover:text-gray-800"
					>
						<X className="h-5 w-5" aria-hidden />
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
