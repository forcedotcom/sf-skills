import type { DateRange } from "react-day-picker";
import {
	DatePicker,
	DatePickerRangeTrigger,
	DatePickerContent,
	DatePickerCalendar,
} from "../../../../components/ui/datePicker";

import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import type { FilterFieldType } from "../../utils/filterUtils";
import { toDate, toDateString } from "./DateFilter";

interface DateRangeFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	helpText?: string;
	filterType?: FilterFieldType;
}

export function DateRangeFilter({
	field,
	label,
	helpText,
	filterType = "daterange",
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
				type: filterType,
				min: toDateString(range?.from),
				max: toDateString(range?.to),
			});
		}
	}

	return (
		<FilterFieldWrapper label={label} helpText={helpText} className={className} {...props}>
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
		</FilterFieldWrapper>
	);
}
