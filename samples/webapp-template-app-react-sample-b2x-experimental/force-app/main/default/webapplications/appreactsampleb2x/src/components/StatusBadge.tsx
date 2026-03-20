import { Check } from "lucide-react";

interface StatusBadgeProps {
	status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
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
			className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${getStyle()}`}
		>
			{showCheckmark && <Check className="size-4" aria-hidden />}
			{showDot && <span className="size-2 rounded-full bg-current" aria-hidden />}
			{getLabel()}
		</span>
	);
}
