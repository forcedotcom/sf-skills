/**
 * Single maintenance request row: icon (teal) | Type & address + title | tenant (gray circle) [| status].
 */
import { useCallback } from "react";
import type { MaintenanceRequestSummary } from "@/api/maintenanceRequests/maintenanceRequestApi";
import { MaintenanceRequestIcon } from "@/components/maintenanceRequests/MaintenanceRequestIcon";
import { StatusBadge } from "@/components/maintenanceRequests/StatusBadge";

export interface MaintenanceRequestListItemProps {
	request: MaintenanceRequestSummary;
	/** When set, row is clickable and opens details (e.g. modal). */
	onClick?: (request: MaintenanceRequestSummary) => void;
}

export default function MaintenanceRequestListItem({
	request,
	onClick,
}: MaintenanceRequestListItemProps) {
	const issueType = request.type ?? "General";
	const addressFirstPart = request.propertyAddress
		? request.propertyAddress.split(",")[0].trim()
		: (request.name ?? "—");
	const title = request.title?.trim() || request.name?.trim() || "—";

	const handleClick = useCallback(() => {
		onClick?.(request);
	}, [onClick, request]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (onClick && (e.key === "Enter" || e.key === " ")) {
				e.preventDefault();
				onClick(request);
			}
		},
		[onClick, request],
	);

	const isClickable = Boolean(onClick);

	return (
		<div
			className={`flex items-center p-4 bg-gray-50 rounded-lg transition-colors ${isClickable ? "cursor-pointer hover:bg-gray-100" : ""}`}
			onClick={isClickable ? handleClick : undefined}
			onKeyDown={isClickable ? handleKeyDown : undefined}
			role={isClickable ? "button" : undefined}
			tabIndex={isClickable ? 0 : undefined}
			aria-label={
				isClickable
					? `View details for ${title !== "—" ? title : "maintenance request"}`
					: undefined
			}
		>
			<MaintenanceRequestIcon type={request.type} />

			{/* Issue Type and Address - Fixed width; title below to save space (avoids clipping) */}
			<div className="ml-4 min-w-0 grow">
				<div className="flex items-center gap-2 mb-1">
					<h3 className="font-semibold text-gray-900 truncate">{issueType}</h3>
					<span className="text-gray-500 flex-shrink-0">|</span>
					<span className="text-sm text-gray-600 truncate">{addressFirstPart}</span>
				</div>
				<p className="text-base text-gray-700 truncate" title={title !== "—" ? title : undefined}>
					{title}
				</p>
			</div>

			<div className="ml-4 flex flex-shrink-0 items-center">
				<StatusBadge status={request.status ?? "—"} />
			</div>
		</div>
	);
}
