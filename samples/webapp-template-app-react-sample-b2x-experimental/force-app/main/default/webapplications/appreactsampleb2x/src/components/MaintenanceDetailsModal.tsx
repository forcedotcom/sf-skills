/**
 * Modal showing maintenance request details. Read-only (no status update in B2X).
 * Layout matches B2E MaintenanceDetailsModal.
 */
import { useEffect } from "react";
import { X } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import type { MaintenanceRequestSummary } from "@/api/maintenanceRequestApi";

export interface MaintenanceDetailsModalProps {
	request: MaintenanceRequestSummary;
	isOpen: boolean;
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

export default function MaintenanceDetailsModal({
	request,
	isOpen,
	onClose,
}: MaintenanceDetailsModalProps) {
	useEffect(() => {
		if (!isOpen) return;
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		document.addEventListener("keydown", handleEscape);
		return () => document.removeEventListener("keydown", handleEscape);
	}, [isOpen, onClose]);

	if (!isOpen) return null;

	const description = request.description?.trim() || request.title?.trim() || "—";

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center">
			{/* Backdrop */}
			<div className="fixed inset-0 bg-black/50" onClick={onClose} aria-hidden />

			{/* Modal */}
			<div
				className="relative z-10 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto rounded-2xl bg-card shadow-xl border border-border"
				role="dialog"
				aria-modal="true"
				aria-labelledby="maintenance-details-title"
			>
				{/* Header */}
				<div className="flex items-center justify-between border-b border-border p-6">
					<h2 id="maintenance-details-title" className="text-xl font-semibold text-foreground">
						Maintenance Request Details
					</h2>
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
						aria-label="Close"
					>
						<X className="size-6" />
					</button>
				</div>

				{/* Content */}
				<div className="space-y-6 p-6">
					<div>
						<h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
							Description
						</h3>
						<p className="text-base text-foreground">{description}</p>
					</div>

					<div className="grid grid-cols-2 gap-4">
						<div>
							<h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
								Issue Type
							</h3>
							<p className="text-base text-foreground">{request.type ?? "—"}</p>
						</div>
						<div>
							<h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
								Priority
							</h3>
							<p className="text-base text-foreground">{request.priority ?? "—"}</p>
						</div>
					</div>

					<div>
						<h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
							Property
						</h3>
						<p className="text-base text-foreground">{request.propertyAddress?.trim() || "—"}</p>
					</div>

					<div>
						<h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
							Tenant
						</h3>
						<p className="text-base text-foreground">{request.tenantName?.trim() || "—"}</p>
					</div>

					<div>
						<h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
							Scheduled Date
						</h3>
						<p className="text-base text-foreground">{formatDate(request.dateRequested)}</p>
					</div>

					<div>
						<h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
							Status
						</h3>
						<StatusBadge status={request.status ?? "—"} />
					</div>
				</div>
			</div>
		</div>
	);
}
