import { useState } from "react";
import { parseISO } from "date-fns";
import {
	DatePicker,
	DatePickerTrigger,
	DatePickerContent,
	DatePickerCalendar,
} from "../../../../components/ui/datePicker";

import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import type { FilterFieldType } from "../../utils/filterUtils";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";

type DateOperator = "gt" | "lt";

const OPERATOR_OPTIONS: { value: DateOperator; label: string }[] = [
	{ value: "gt", label: "After" },
	{ value: "lt", label: "Before" },
];

function operatorToField(op: DateOperator): "min" | "max" {
	return op === "gt" ? "min" : "max";
}

interface DateFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	helpText?: string;
	filterType?: FilterFieldType;
}

export function DateFilter({
	field,
	label,
	helpText,
	filterType = "date",
	className,
	...props
}: DateFilterProps) {
	const { value, onChange } = useFilterField(field);

	const initialOp: DateOperator = value?.min ? "gt" : "lt";
	const [operator, setOperator] = useState<DateOperator>(initialOp);

	const currentDate = toDate(value?.min ?? value?.max);

	function handleOperatorChange(op: DateOperator) {
		setOperator(op);
		if (currentDate) {
			emitChange(op, currentDate);
		}
	}

	function handleDateChange(date: Date | undefined) {
		if (!date) {
			onChange(undefined);
		} else {
			emitChange(operator, date);
		}
	}

	function emitChange(op: DateOperator, date: Date) {
		const dateStr = toDateString(date);
		const f = operatorToField(op);
		onChange({
			field,
			label,
			type: filterType,
			value: op,
			min: f === "min" ? dateStr : undefined,
			max: f === "max" ? dateStr : undefined,
		});
	}

	return (
		<FilterFieldWrapper label={label} helpText={helpText} className={className} {...props}>
			<div className="flex gap-2">
				<Select value={operator} onValueChange={(v) => handleOperatorChange(v as DateOperator)}>
					<SelectTrigger className="w-full flex-1">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						{OPERATOR_OPTIONS.map((opt) => (
							<SelectItem key={opt.value} value={opt.value}>
								{opt.label}
							</SelectItem>
						))}
					</SelectContent>
				</Select>
				<DatePicker>
					<DatePickerTrigger
						className="w-full flex-2"
						date={currentDate}
						dateFormat="MMM do, yyyy"
						placeholder="Pick a date"
						aria-label={label}
					/>
					<DatePickerContent>
						<DatePickerCalendar
							mode="single"
							captionLayout="dropdown"
							selected={currentDate}
							onSelect={handleDateChange}
						/>
					</DatePickerContent>
				</DatePicker>
			</div>
		</FilterFieldWrapper>
	);
}

export function toDate(value: string | undefined): Date | undefined {
	if (!value) return undefined;
	const parsed = parseISO(value);
	return isNaN(parsed.getTime()) ? undefined : parsed;
}

export function toDateString(date: Date | undefined): string {
	if (!date) return "";
	return date.toISOString().split("T")[0];
}
