import type { DateRange } from "react-day-picker";
import { Label } from "../../../../components/ui/label";
import {
	DatePicker,
	DatePickerRangeTrigger,
	DatePickerContent,
	DatePickerCalendar,
} from "../../../../components/ui/datePicker";
import { cn } from "../../../../lib/utils";
import type { FilterFieldConfig, ActiveFilterValue } from "../../utils/filterUtils";
import { toDate, toDateString } from "./DateFilter";

interface DateRangeFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	labelProps?: React.ComponentProps<typeof Label>;
	helpTextProps?: React.ComponentProps<"p">;
}

export function DateRangeFilter({
	config,
	value,
	onChange,
	className,
	labelProps,
	helpTextProps,
	...props
}: DateRangeFilterProps) {
	const dateRange: DateRange | undefined =
		value?.min || value?.max ? { from: toDate(value?.min), to: toDate(value?.max) } : undefined;

	function handleRangeSelect(range: DateRange | undefined) {
		if (!range?.from && !range?.to) {
			onChange(undefined);
		} else {
			onChange({
				field: config.field,
				label: config.label,
				type: "daterange",
				min: toDateString(range?.from),
				max: toDateString(range?.to),
			});
		}
	}

	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label {...labelProps}>{labelProps?.children ?? config.label}</Label>
			<DatePicker>
				<DatePickerRangeTrigger
					className="w-full"
					dateRange={dateRange}
					placeholder="Pick a date range"
					aria-label={config.label}
				/>
				<DatePickerContent align="start">
					<DatePickerCalendar
						mode="range"
						captionLayout="dropdown"
						defaultMonth={dateRange?.from}
						selected={dateRange}
						onSelect={handleRangeSelect}
						numberOfMonths={2}
					/>
				</DatePickerContent>
			</DatePicker>
			{config.helpText && (
				<p
					{...helpTextProps}
					className={cn("text-xs text-muted-foreground", helpTextProps?.className)}
				>
					{helpTextProps?.children ?? config.helpText}
				</p>
			)}
		</div>
	);
}
