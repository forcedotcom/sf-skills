/**
 * UnifiedSearch — the single search surface for the whole app.
 *
 * A thin wrapper over feature-react-search's drop-in `<Search>` (see
 * `lib/searchConfig.ts` for the source definitions and the `pagination.mode:
 * "merged"` that selects the combined-grid layout). The feature owns all the
 * search chrome — search bar, scope selector, single-source filter/sort panel,
 * the results count, the merged card grid, and one global pager over the
 * cumulative result set. This component supplies only what's app-specific:
 *
 *   - **Cards** — one per object type, via `renderResult` keyed by source.
 *   - **Detail modals** — opened on card click; maintenance requests and
 *     applications also support an inline status update. Because the search
 *     hook exposes no refetch, saved statuses are reflected optimistically via
 *     `statusOverrides`.
 *
 * The per-card source badge in the mixed ("All") grid is supplied by the feature
 * automatically (each source's `label`, auto-colored) — no app code needed.
 *
 * One implementation serves both the unified `/search` page (no `restrictTo`)
 * and each single-object page (`restrictTo="properties"` etc.): passing
 * `restrictTo` locks the scope, hides the selector, and collapses the grid to
 * that one source.
 */

import { useCallback, useRef, useState } from "react";
import { Search, type SearchConfig } from "../../features/search";
import { toast } from "../ui/sonner";
import { searchConfig, SOURCE_KEYS, type SourceKey } from "../../lib/searchConfig";
import { PropertyCard } from "../properties/PropertyCard";
import { MaintenanceRequestCard } from "../maintenanceRequests/MaintenanceRequestCard";
import { WorkerCard } from "../maintenanceWorkers/WorkerCard";
import { ApplicationCard } from "../applications/ApplicationCard";
import { PropertyDetailsModal } from "../properties/PropertyDetailsModal";
import { MaintenanceDetailsModal } from "../maintenanceRequests/MaintenanceDetailsModal";
import { WorkerDetailsModal } from "../maintenanceWorkers/WorkerDetailsModal";
import { ApplicationDetailsModal } from "../applications/ApplicationDetailsModal";
import type { PropertySearchNode } from "../../api/properties/propertySearchService";
import type { MaintenanceRequestSearchNode } from "../../api/maintenanceRequests/maintenanceRequestSearchService";
import type { MaintenanceWorkerSearchNode } from "../../api/maintenanceWorkers/maintenanceWorkerSearchService";
import type { ApplicationSearchNode } from "../../api/applications/applicationSearchService";
import { updateMaintenanceStatus } from "../../api/maintenanceRequests/maintenanceRequests";
import { updateApplicationStatus } from "../../api/applications/applications";

const config: SearchConfig = searchConfig;

export interface UnifiedSearchProps {
	title?: string;
	subtitle?: string;
	searchPlaceholder?: string;
	/** Lock the search to a single source; hides the scope selector. */
	restrictTo?: SourceKey;
}

/** Discriminated handle on the record whose detail modal is open. */
type Selected =
	| { key: typeof SOURCE_KEYS.PROPERTIES; node: PropertySearchNode }
	| { key: typeof SOURCE_KEYS.MAINTENANCE; node: MaintenanceRequestSearchNode }
	| { key: typeof SOURCE_KEYS.WORKERS; node: MaintenanceWorkerSearchNode }
	| { key: typeof SOURCE_KEYS.APPLICATIONS; node: ApplicationSearchNode };

type StatusNode = {
	Id: string;
	Status__c?: { value?: string | null; displayValue?: string | null } | null;
};

/** Returns a copy of `node` with its status replaced by an optimistic override, if any. */
function withStatusOverride<T extends StatusNode>(node: T, overrides: Record<string, string>): T {
	const next = overrides[node.Id];
	if (next == null) return node;
	return { ...node, Status__c: { ...(node.Status__c ?? {}), value: next, displayValue: next } };
}

export function UnifiedSearch({
	title = "Search",
	subtitle,
	searchPlaceholder = "Search…",
	restrictTo,
}: UnifiedSearchProps) {
	const [selected, setSelected] = useState<Selected | null>(null);
	const [statusOverrides, setStatusOverrides] = useState<Record<string, string>>({});
	const triggerRef = useRef<HTMLElement | null>(null);

	const openModal = useCallback((value: Selected) => {
		triggerRef.current = document.activeElement as HTMLElement;
		setSelected(value);
	}, []);

	const closeModal = useCallback(() => {
		const trigger = triggerRef.current;
		triggerRef.current = null;
		setSelected(null);
		// Use rAF to focus after Radix Dialog has finished its own focus management
		requestAnimationFrame(() => trigger?.focus());
	}, []);

	// -- Optimistic status save -------------------------------------------------

	const applyOptimisticStatus = useCallback((key: Selected["key"], id: string, status: string) => {
		setStatusOverrides((prev) => ({ ...prev, [id]: status }));
		setSelected((prev) => {
			if (!prev || prev.key !== key || prev.node.Id !== id) return prev;
			// Only the status-bearing sources (maintenance, applications) reach
			// here; cast through StatusNode so the union's non-status members
			// don't trip the type checker.
			const current = prev.node as StatusNode;
			return {
				...prev,
				node: {
					...prev.node,
					Status__c: { ...(current.Status__c ?? {}), value: status, displayValue: status },
				},
			} as Selected;
		});
	}, []);

	const handleMaintenanceSave = useCallback(
		async (id: string, status: string) => {
			const ok = await updateMaintenanceStatus(id, status);
			if (!ok) {
				toast.error("Update failed", {
					description: "Could not update the maintenance request. Please try again.",
				});
				throw new Error("Failed to update maintenance status");
			}
			applyOptimisticStatus(SOURCE_KEYS.MAINTENANCE, id, status);
			toast.success("Status updated", {
				description: "Maintenance request status has been updated.",
			});
		},
		[applyOptimisticStatus],
	);

	const handleApplicationSave = useCallback(
		async (id: string, status: string) => {
			const ok = await updateApplicationStatus(id, status);
			if (!ok) {
				toast.error("Update failed", {
					description: "Could not update the application. Please try again.",
				});
				throw new Error("Failed to update application status");
			}
			applyOptimisticStatus(SOURCE_KEYS.APPLICATIONS, id, status);
			toast.success("Status updated", {
				description: "Application status has been updated.",
			});
		},
		[applyOptimisticStatus],
	);

	// -- Card rendering ---------------------------------------------------------

	const renderResult = {
		[SOURCE_KEYS.PROPERTIES]: (node: unknown) => {
			const property = node as PropertySearchNode;
			return (
				<PropertyCard
					property={property}
					onClick={() => openModal({ key: SOURCE_KEYS.PROPERTIES, node: property })}
				/>
			);
		},
		[SOURCE_KEYS.MAINTENANCE]: (node: unknown) => {
			const request = withStatusOverride(node as MaintenanceRequestSearchNode, statusOverrides);
			return (
				<MaintenanceRequestCard
					request={request}
					onClick={() => openModal({ key: SOURCE_KEYS.MAINTENANCE, node: request })}
				/>
			);
		},
		[SOURCE_KEYS.WORKERS]: (node: unknown) => {
			const worker = node as MaintenanceWorkerSearchNode;
			return (
				<WorkerCard
					worker={worker}
					onClick={() => openModal({ key: SOURCE_KEYS.WORKERS, node: worker })}
				/>
			);
		},
		[SOURCE_KEYS.APPLICATIONS]: (node: unknown) => {
			const application = withStatusOverride(node as ApplicationSearchNode, statusOverrides);
			return (
				<ApplicationCard
					application={application}
					onClick={() => openModal({ key: SOURCE_KEYS.APPLICATIONS, node: application })}
				/>
			);
		},
	};

	return (
		<>
			<Search
				config={config}
				title={title}
				subtitle={subtitle}
				searchPlaceholder={searchPlaceholder}
				restrictTo={restrictTo ? { kind: "sobject", key: restrictTo } : undefined}
				renderResult={renderResult}
			/>

			{selected?.key === SOURCE_KEYS.PROPERTIES && (
				<PropertyDetailsModal property={selected.node} isOpen onClose={closeModal} />
			)}
			{selected?.key === SOURCE_KEYS.MAINTENANCE && (
				<MaintenanceDetailsModal
					request={selected.node}
					isOpen
					onClose={closeModal}
					onSave={handleMaintenanceSave}
				/>
			)}
			{selected?.key === SOURCE_KEYS.WORKERS && (
				<WorkerDetailsModal worker={selected.node} isOpen onClose={closeModal} />
			)}
			{selected?.key === SOURCE_KEYS.APPLICATIONS && (
				<ApplicationDetailsModal
					application={selected.node}
					isOpen
					onClose={closeModal}
					onSave={handleApplicationSave}
				/>
			)}
		</>
	);
}
