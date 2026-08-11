import React from "react";
import { FileText, User, Home, CalendarDays } from "lucide-react";
import type { ApplicationSearchNode } from "../../api/applications/applicationSearchService";

interface ApplicationCardProps {
	application: ApplicationSearchNode;
	onClick?: (application: ApplicationSearchNode) => void;
}

function statusColor(status: string): string {
	const s = status.toLowerCase();
	if (s.includes("approved")) return "bg-green-100 text-green-700";
	if (s.includes("rejected")) return "bg-red-100 text-red-700";
	if (s.includes("background")) return "bg-blue-100 text-blue-700";
	if (s.includes("review")) return "bg-yellow-100 text-yellow-700";
	return "bg-gray-100 text-gray-700";
}

function formatDate(value: string | null | undefined): string | undefined {
	if (!value) return undefined;
	const date = new Date(value);
	if (isNaN(date.getTime())) return undefined;
	return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export const ApplicationCard: React.FC<ApplicationCardProps> = ({ application, onClick }) => {
	const name = application.Name?.value || "Application";
	const applicant = application.User__r?.Name?.value || "Unknown applicant";
	const propertyName = application.Property__r?.Name?.value;
	const propertyAddress = application.Property__r?.Address__c?.value;
	const status = application.Status__c?.value || "Unknown";
	const startDate = formatDate(application.Start_Date__c?.value);

	const handleClick = () => onClick?.(application);

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
					<FileText className="w-5 h-5 text-purple-600 shrink-0" />
					<h2 className="text-base font-semibold text-gray-900 truncate">{name}</h2>
				</div>
				<span
					className={`shrink-0 px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor(status)}`}
				>
					{status}
				</span>
			</div>

			<div className="mt-auto space-y-1 text-sm text-gray-600">
				<div className="flex items-center gap-2">
					<User className="w-4 h-4 text-gray-400 shrink-0" />
					<span className="truncate">{applicant}</span>
				</div>
				<div className="flex items-center gap-2">
					<Home className="w-4 h-4 text-gray-400 shrink-0" />
					<span className="truncate">{propertyName || propertyAddress || "Unknown property"}</span>
				</div>
				{startDate && (
					<div className="flex items-center gap-2">
						<CalendarDays className="w-4 h-4 text-gray-400 shrink-0" />
						<span className="truncate">Starts {startDate}</span>
					</div>
				)}
			</div>
		</div>
	);
};
