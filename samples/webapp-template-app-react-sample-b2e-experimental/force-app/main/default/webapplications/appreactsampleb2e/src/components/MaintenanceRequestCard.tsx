import React from "react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import type { MaintenanceRequest } from "../lib/types";

interface MaintenanceRequestCardProps {
	request: MaintenanceRequest;
	onView: (id: string) => void;
}

const priorityConfig: Record<
	"Emergency (2hr)" | "High (Same Day)" | "Standard",
	{ color: string; label: string; emoji: string }
> = {
	"Emergency (2hr)": { color: "text-red-500", label: "EMERGENCY (2HR)", emoji: "🔴" },
	"High (Same Day)": { color: "text-orange-500", label: "HIGH (SAME DAY)", emoji: "🟠" },
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
	const priority = priorityConfig[request.priority];
	const issueIcon = issueIcons[request.issueType] || "🔧";

	return (
		<Card className="p-4 mb-3">
			<div className="space-y-2">
				<div className="flex items-start justify-between gap-4">
					<div className="flex items-start gap-2 flex-1">
						<span className={`${priority.color} font-bold text-sm`}>
							{priority.emoji} {priority.label}
						</span>
						<span className="text-gray-700 font-medium">{request.propertyAddress}</span>
					</div>
					<span className="text-sm text-gray-500 uppercase">{request.status}</span>
				</div>

				<div className="flex items-center gap-2">
					<span className="text-xl">{issueIcon}</span>
					<span className="text-sm text-gray-700">
						{request.issueType} - {request.description}
					</span>
				</div>

				{request.assignedWorker && (
					<div className="text-sm text-gray-600">👷 Assigned to: {request.assignedWorker}</div>
				)}

				{request.scheduledDateTime && (
					<div className="flex items-center justify-between">
						<div className="text-sm text-gray-600">📅 Scheduled: {request.scheduledDateTime}</div>
						<Button onClick={() => onView(request.id)} variant="outline" size="sm">
							View
						</Button>
					</div>
				)}
			</div>
		</Card>
	);
};
