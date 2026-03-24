import type { DateRange } from "react-day-picker";
import { Label } from "../../../../components/ui/label";
import {
	DatePicker,
	DatePickerRangeTrigger,
	DatePickerContent,
	DatePickerCalendar,
} from "../../../../components/ui/datePicker";
import { cn } from "../../../../lib/utils";
import { useFilterField } from "../FilterContext";
import { toDate, toDateString } from "./DateFilter";

interface DateRangeFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	helpText?: string;
}

export function DateRangeFilter({
	field,
	label,
	helpText,
	className,
	...props
}: DateRangeFilterProps) {
	const { value, onChange } = useFilterField(field);

	const dateRange: DateRange | undefined =
		value?.min || value?.max ? { from: toDate(value?.min), to: toDate(value?.max) } : undefined;

	function handleRangeSelect(range: DateRange | undefined) {
		if (!range?.from && !range?.to) {
			onChange(undefined);
		} else {
			onChange({
				field,
				label,
				type: "daterange",
				min: toDateString(range?.from),
				max: toDateString(range?.to),
			});
		}
	}

	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label>{label}</Label>
			<DatePicker>
				<DatePickerRangeTrigger
					className="w-full"
					dateRange={dateRange}
					placeholder="Pick a date range"
					aria-label={label}
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
			{helpText && <p className="text-xs text-muted-foreground">{helpText}</p>}
		</div>
	);
}
