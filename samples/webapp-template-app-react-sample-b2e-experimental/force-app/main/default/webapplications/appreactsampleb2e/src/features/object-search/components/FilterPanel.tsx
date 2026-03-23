import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "../../../components/ui/collapsible";
import { cn } from "../../../lib/utils";
import { ChevronDown } from "lucide-react";
import { useState } from "react";
import type { FilterFieldConfig, ActiveFilterValue } from "../utils/filterUtils";
import { TextFilter } from "./filters/TextFilter";
import { SelectFilter } from "./filters/SelectFilter";
import { NumericRangeFilter } from "./filters/NumericRangeFilter";
import { BooleanFilter } from "./filters/BooleanFilter";
import { DateFilter } from "./filters/DateFilter";
import { DateRangeFilter } from "./filters/DateRangeFilter";
import { MultiSelectFilter } from "./filters/MultiSelectFilter";
import { SearchFilter } from "./filters/SearchFilter";

interface FilterPanelProps extends Omit<React.ComponentProps<"div">, "onReset"> {
	configs: FilterFieldConfig[];
	filters: ActiveFilterValue[];
	onFilterChange: (field: string, value: ActiveFilterValue | undefined) => void;
	onReset: () => void;
	headerProps?: React.ComponentProps<typeof CardHeader>;
	titleProps?: React.ComponentProps<typeof CardTitle>;
	contentProps?: React.ComponentProps<typeof CardContent>;
	resetButtonProps?: React.ComponentProps<typeof Button>;
	toggleButtonProps?: React.ComponentProps<typeof Button>;
}

function getFilterValue(
	filters: ActiveFilterValue[],
	field: string,
): ActiveFilterValue | undefined {
	return filters.find((f) => f.field === field);
}

function renderFilter(
	config: FilterFieldConfig,
	value: ActiveFilterValue | undefined,
	onChange: (value: ActiveFilterValue | undefined) => void,
) {
	switch (config.type) {
		case "text":
			return <TextFilter config={config} value={value} onChange={onChange} />;
		case "picklist":
			return <SelectFilter config={config} value={value} onChange={onChange} />;
		case "numeric":
			return <NumericRangeFilter config={config} value={value} onChange={onChange} />;
		case "boolean":
			return <BooleanFilter config={config} value={value} onChange={onChange} />;
		case "date":
			return <DateFilter config={config} value={value} onChange={onChange} />;
		case "daterange":
			return <DateRangeFilter config={config} value={value} onChange={onChange} />;
		case "multipicklist":
			return <MultiSelectFilter config={config} value={value} onChange={onChange} />;
		case "search":
			return <SearchFilter config={config} value={value} onChange={onChange} />;
	}
}

export function FilterPanel({
	configs,
	filters,
	onFilterChange,
	onReset,
	className,
	headerProps,
	titleProps,
	contentProps,
	resetButtonProps,
	toggleButtonProps,
	...props
}: FilterPanelProps) {
	const [open, setOpen] = useState(true);
	const hasActiveFilters = filters.length > 0;

	return (
		<Card className={cn(className)} {...props}>
			<Collapsible open={open} onOpenChange={setOpen}>
				<CardHeader
					{...headerProps}
					className={cn(
						"flex flex-row items-center justify-between space-y-0 pb-2",
						headerProps?.className,
					)}
				>
					<CardTitle
						{...titleProps}
						className={cn("text-base font-semibold", titleProps?.className)}
					>
						{titleProps?.children ?? <h2>Filters</h2>}
					</CardTitle>
					<div className="flex items-center gap-1">
						{hasActiveFilters && (
							<Button variant="destructive" size="sm" onClick={onReset} {...resetButtonProps}>
								{resetButtonProps?.children ?? "Reset"}
							</Button>
						)}
						<CollapsibleTrigger asChild>
							<Button variant="ghost" size="icon" {...toggleButtonProps}>
								<ChevronDown
									className={`h-4 w-4 transition-transform ${open ? "" : "-rotate-90"}`}
								/>
								<span className="sr-only">Toggle filters</span>
							</Button>
						</CollapsibleTrigger>
					</div>
				</CardHeader>
				<CollapsibleContent>
					<CardContent {...contentProps} className={cn("space-y-4 pt-0", contentProps?.className)}>
						{configs.map((config) => (
							<div key={config.field}>
								{renderFilter(config, getFilterValue(filters, config.field), (value) =>
									onFilterChange(config.field, value),
								)}
							</div>
						))}
					</CardContent>
				</CollapsibleContent>
			</Collapsible>
		</Card>
	);
}
