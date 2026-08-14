import { X } from "lucide-react";
import { Button } from "../../../../components/ui/button";
import type { ActiveFilterValue } from "../../utils/filterUtils";

function formatLabel(filter: ActiveFilterValue): string {
	const { label, type, value, min, max } = filter;
	switch (type) {
		case "text":
		case "picklist":
			return `${label}: ${value ?? ""}`;
		case "multipicklist": {
			const values = value ? value.split(",") : [];
			if (values.length <= 2) return `${label}: ${values.join(", ")}`;
			return `${label}: ${values.length} selected`;
		}
		case "boolean":
			return `${label}: ${value === "true" ? "Yes" : "No"}`;
		case "numeric": {
			if (min && max) return `${label}: ${min} – ${max}`;
			if (min) return `${label}: ≥ ${min}`;
			return `${label}: ≤ ${max ?? ""}`;
		}
		case "date":
		case "daterange":
		case "datetime":
		case "datetimerange": {
			if (min && max) return `${label}: ${min} → ${max}`;
			if (min) return `${label}: from ${min}`;
			return `${label}: until ${max ?? ""}`;
		}
		default:
			return label;
	}
}

interface ActiveFiltersProps {
	filters: ActiveFilterValue[];
	onRemove: (field: string) => void;
	className?: string;
}

export function ActiveFilters({ filters, onRemove, className }: ActiveFiltersProps) {
	if (filters.length === 0) return null;
	return (
		<div className={`flex flex-wrap gap-2 ${className ?? ""}`}>
			{filters.map((filter) => (
				<Button
					key={filter.field}
					variant="outline"
					size="sm"
					className="gap-1 h-7 text-xs"
					aria-label={`Remove ${formatLabel(filter)}`}
					onClick={() => onRemove(filter.field)}
				>
					{formatLabel(filter)}
					<X className="h-3 w-3" aria-hidden="true" />
				</Button>
			))}
		</div>
	);
}
