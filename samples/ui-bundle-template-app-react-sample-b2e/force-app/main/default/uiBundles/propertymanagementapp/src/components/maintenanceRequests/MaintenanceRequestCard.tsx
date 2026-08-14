import React from "react";
import { Wrench, MapPin, User, CalendarClock } from "lucide-react";
import type { MaintenanceRequestSearchNode } from "../../api/maintenanceRequests/maintenanceRequestSearchService";

interface MaintenanceRequestCardProps {
	request: MaintenanceRequestSearchNode;
	onClick?: (request: MaintenanceRequestSearchNode) => void;
}

const priorityStyles: Record<string, string> = {
	Emergency: "bg-red-100 text-red-700",
	High: "bg-orange-100 text-orange-700",
	Standard: "bg-blue-100 text-blue-700",
};

const statusStyles: Record<string, string> = {
	New: "bg-purple-100 text-purple-700",
	Assigned: "bg-blue-100 text-blue-700",
	"In Progress": "bg-yellow-100 text-yellow-700",
	"On Hold": "bg-gray-100 text-gray-700",
	Resolved: "bg-green-100 text-green-700",
};

export const MaintenanceRequestCard: React.FC<MaintenanceRequestCardProps> = ({
	request,
	onClick,
}) => {
	const name = request.Name?.value || "Request";
	const issueType = request.Type__c?.value || "General";
	const priority = request.Priority__c?.value || "Standard";
	const status = request.Status__c?.value || "New";
	const description = request.Description__c?.value || "No description provided.";
	const propertyAddress = request.Property__r?.Address__c?.value || "Unknown address";
	const assignedWorker = request.Assigned_Worker__r?.Name?.value;
	const scheduled = request.Scheduled__c?.value
		? new Date(request.Scheduled__c.value).toLocaleString(undefined, {
				month: "short",
				day: "numeric",
				hour: "numeric",
				minute: "2-digit",
			})
		: undefined;

	const handleClick = () => onClick?.(request);

	return (
		<div
			role="button"
			tabIndex={0}
			aria-label={name}
			className="h-full bg-white rounded-lg shadow-md p-5 hover:shadow-lg transition-shadow cursor-pointer flex flex-col gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-purple focus-visible:ring-offset-2"
			onClick={handleClick}
			onKeyDown={(e) => {
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					handleClick();
				}
			}}
		>
			<div className="flex items-start justify-between gap-2">
				<div className="flex items-center gap-2 min-w-0">
					<Wrench className="w-5 h-5 text-purple-600 shrink-0" />
					<h2 className="text-base font-semibold text-gray-900 truncate">{name}</h2>
				</div>
				<span
					className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium ${
						statusStyles[status] ?? "bg-gray-100 text-gray-700"
					}`}
				>
					{status}
				</span>
			</div>

			<div className="flex flex-wrap items-center gap-2">
				<span
					className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
						priorityStyles[priority] ?? priorityStyles.Standard
					}`}
				>
					{priority}
				</span>
				<span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
					{issueType}
				</span>
			</div>

			<p className="text-sm text-gray-700 line-clamp-2">{description}</p>

			<div className="mt-auto space-y-1 text-sm text-gray-600">
				<div className="flex items-center gap-2">
					<MapPin className="w-4 h-4 text-gray-400 shrink-0" />
					<span className="truncate">{propertyAddress}</span>
				</div>
				<div className="flex items-center gap-2">
					<User className="w-4 h-4 text-gray-400 shrink-0" />
					<span className="truncate">{assignedWorker || "Unassigned"}</span>
				</div>
				{scheduled && (
					<div className="flex items-center gap-2">
						<CalendarClock className="w-4 h-4 text-gray-400 shrink-0" />
						<span className="truncate">{scheduled}</span>
					</div>
				)}
			</div>
		</div>
	);
};
