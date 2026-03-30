import { X } from "lucide-react";
import { Button } from "../../../components/ui/button";
import { cn } from "../../../lib/utils";
import type { ActiveFilterValue } from "../utils/filterUtils";

function formatFilterLabel(filter: ActiveFilterValue): string {
	const { label, type, value, min, max } = filter;

	switch (type) {
		case "search":
			return `Search: ${value}`;
		case "text":
		case "picklist":
			return `${label}: ${value}`;
		case "multipicklist": {
			const values = value ? value.split(",") : [];
			if (values.length <= 2) return `${label}: ${values.join(", ")}`;
			return `${label}: ${values.length} selected`;
		}
		case "boolean":
			return `${label}: ${value === "true" ? "Yes" : "No"}`;
		case "numeric": {
			if (min && max) return `${label}: ${min} - ${max}`;
			if (min) return `${label}: >= ${min}`;
			return `${label}: <= ${max}`;
		}
		case "date": {
			if (min && max) return `${label}: ${min} to ${max}`;
			if (min) return `${label}: from ${min}`;
			return `${label}: until ${max}`;
		}
		default:
			return label;
	}
}

interface ActiveFiltersProps extends React.ComponentProps<"div"> {
	filters: ActiveFilterValue[];
	onRemove: (field: string) => void;
	buttonProps?: Omit<React.ComponentProps<typeof ActiveFilterButton>, "filter" | "onRemove">;
}

export function ActiveFilters({
	filters,
	onRemove,
	className,
	buttonProps,
	...props
}: ActiveFiltersProps) {
	if (filters.length === 0) return null;

	return (
		<div className={cn("flex flex-wrap gap-2", className)} {...props}>
			{filters.map((filter) => (
				<ActiveFilterButton
					key={filter.field}
					filter={filter}
					onRemove={onRemove}
					{...buttonProps}
				/>
			))}
		</div>
	);
}

interface ActiveFilterButtonProps extends React.ComponentProps<typeof Button> {
	filter: ActiveFilterValue;
	onRemove: (field: string) => void;
}

export function ActiveFilterButton({
	filter,
	onRemove,
	className,
	...props
}: ActiveFilterButtonProps) {
	return (
		<Button
			variant="outline"
			size="sm"
			className={cn("gap-1 h-7 text-xs", className)}
			onClick={() => onRemove(filter.field)}
			{...props}
		>
			{formatFilterLabel(filter)}
			<X className="h-3 w-3" />
		</Button>
	);
}
