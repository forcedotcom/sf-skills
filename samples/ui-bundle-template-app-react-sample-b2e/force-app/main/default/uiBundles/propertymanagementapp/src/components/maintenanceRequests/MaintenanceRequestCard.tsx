import React from "react";
import { Card } from "../ui/card";
import { Button } from "../ui/button";
import type { MaintenanceRequestSearchNode } from "../../api/maintenanceRequests/maintenanceRequestSearchService";

interface MaintenanceRequestCardProps {
	request: MaintenanceRequestSearchNode;
	onView: (id: string) => void;
}

const priorityConfig: Record<
	"Emergency" | "High" | "Standard",
	{ color: string; label: string; emoji: string }
> = {
	Emergency: { color: "text-red-500", label: "EMERGENCY (2HR)", emoji: "🔴" },
	High: { color: "text-orange-500", label: "HIGH (SAME DAY)", emoji: "🟠" },
	Standard: { color: "text-blue-500", label: "STANDARD", emoji: "🔵" },
};

const issueIcons: Record<string, string> = {
	Plumbing: "💧",
	HVAC: "❄️",
	Electrical: "🔌",
	Appliance: "🔧",
	Pest: "🐛",
};

export const MaintenanceRequestCard: React.FC<MaintenanceRequestCardProps> = ({
	request,
	onView,
}) => {
	const priorityValue = request.Priority__c?.value;
	const priority =
		priorityConfig[priorityValue as keyof typeof priorityConfig] || priorityConfig.Standard;
	const issueType = request.Type__c?.value || "General";
	const issueIcon = issueIcons[issueType] || "🔧";
	const propertyAddress = request.Property__r?.Address__c?.value || "Unknown Address";
	const status = request.Status__c?.value || "New";
	const description = request.Description__c?.value || "";
	const scheduledDate = request.Scheduled__c?.value
		? new Date(request.Scheduled__c.value).toLocaleString()
		: undefined;
	const assignedWorker = request.Assigned_Worker__r?.Name?.value || "Unassigned";

	return (
		<Card className="p-4 mb-3">
			<div className="space-y-2">
				<div className="flex items-start justify-between gap-4">
					<div className="flex items-start gap-2 flex-1">
						<span className={`${priority.color} font-bold text-sm`}>
							{priority.emoji} {priority.label}
						</span>
						<span className="text-gray-700 font-medium">{propertyAddress}</span>
					</div>
					<span className="text-sm text-gray-500 uppercase">{status}</span>
				</div>

				<div className="flex items-center gap-2">
					<span className="text-xl">{issueIcon}</span>
					<span className="text-sm text-gray-700">
						{issueType} - {description}
					</span>
				</div>

				{assignedWorker && (
					<div className="text-sm text-gray-600">👷 Assigned to: {assignedWorker}</div>
				)}

				{scheduledDate && (
					<div className="flex items-center justify-between">
						<div className="text-sm text-gray-600">📅 Scheduled: {scheduledDate}</div>
						<Button onClick={() => onView(request.Id)} variant="outline" size="sm">
							View
						</Button>
					</div>
				)}
			</div>
		</Card>
	);
};
