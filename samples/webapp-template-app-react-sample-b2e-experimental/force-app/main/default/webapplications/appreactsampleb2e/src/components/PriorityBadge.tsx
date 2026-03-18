import React from "react";

interface PriorityBadgeProps {
	priority: "Emergency (2hr)" | "High (Same Day)" | "Standard";
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
	const styles = {
		"Emergency (2hr)": "bg-red-100 text-red-700 border-red-200",
		"High (Same Day)": "bg-orange-100 text-orange-700 border-orange-200",
		Standard: "bg-blue-100 text-blue-700 border-blue-200",
	};

	const labels = {
		"Emergency (2hr)": "Emergency (2hr)",
		"High (Same Day)": "High (Same Day)",
		Standard: "Standard",
	};

	return (
		<span
			className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[priority]}`}
		>
			{labels[priority]}
		</span>
	);
};
