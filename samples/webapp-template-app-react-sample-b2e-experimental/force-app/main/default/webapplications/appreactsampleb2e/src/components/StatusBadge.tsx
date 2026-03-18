import React from "react";
import { Check } from "lucide-react";

interface StatusBadgeProps {
	status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
	const statusLower = status.toLowerCase();

	const getStyle = () => {
		if (statusLower === "new") return "bg-pink-100 text-pink-700";
		if (statusLower === "in progress") return "bg-yellow-100 text-yellow-700";
		if (statusLower === "resolved") return "bg-green-100 text-green-700";
		return "bg-gray-100 text-gray-700";
	};

	const getLabel = () => {
		if (statusLower === "new") return "Needs Action";
		if (statusLower === "in progress") return "In Progress";
		if (statusLower === "resolved") return "Resolved";
		return status;
	};

	const showCheckmark = statusLower === "resolved";
	const showDot = statusLower === "new" || statusLower === "in progress";

	return (
		<span
			className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${getStyle()}`}
		>
			{showCheckmark && <Check className="w-4 h-4" />}
			{showDot && <span className="w-2 h-2 rounded-full bg-current" />}
			{getLabel()}
		</span>
	);
};
