import { useState } from "react";
import { parseISO } from "date-fns";
import { ChevronDown, Check } from "lucide-react";
import { Label } from "../../../../components/ui/label";
import { Button } from "../../../../components/ui/button";
import {
	Popover,
	PopoverTrigger,
	PopoverContent,
} from "../../../../components/ui/popover";
import {
	DatePicker,
	DatePickerTrigger,
	DatePickerContent,
	DatePickerCalendar,
} from "../../../../components/ui/datePicker";
import { cn } from "../../../../lib/utils";
import type { FilterFieldConfig, ActiveFilterValue } from "../../utils/filterUtils";

type DateOperator = "gt" | "lt";

const OPERATOR_OPTIONS: { value: DateOperator; label: string }[] = [
	{ value: "gt", label: "After" },
	{ value: "lt", label: "Before" },
];

/** Maps operator to the ActiveFilterValue field used to carry the date. */
function operatorToField(op: DateOperator): "min" | "max" {
	return op === "gt" ? "min" : "max";
}

interface DateFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	labelProps?: React.ComponentProps<typeof Label>;
	helpTextProps?: React.ComponentProps<"p">;
}

export function DateFilter({
	config,
	value,
	onChange,
	className,
	labelProps,
	helpTextProps,
	...props
}: DateFilterProps) {
	// Derive initial operator from the existing value (min → gt, max → lt)
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
		const field = operatorToField(op);
		onChange({
			field: config.field,
			label: config.label,
			type: "date",
			value: op,
			min: field === "min" ? dateStr : undefined,
			max: field === "max" ? dateStr : undefined,
		});
	}

	const [operatorOpen, setOperatorOpen] = useState(false);
	const operatorLabel = OPERATOR_OPTIONS.find((o) => o.value === operator)?.label ?? "After";

	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label {...labelProps}>{labelProps?.children ?? config.label}</Label>
			<div className="flex min-w-0 gap-2">
				<Popover open={operatorOpen} onOpenChange={setOperatorOpen}>
					<PopoverTrigger asChild>
						<Button
							variant="outline"
							className="h-9 w-[7rem] shrink-0 justify-between px-2.5 font-normal"
							aria-label="Date operator"
						>
							<span className="truncate">{operatorLabel}</span>
							<ChevronDown className="ml-1 size-4 shrink-0 opacity-50" />
						</Button>
					</PopoverTrigger>
					<PopoverContent align="start" className="w-auto min-w-[7rem] p-1">
						{OPERATOR_OPTIONS.map((opt) => (
							<button
								key={opt.value}
								type="button"
								className={cn(
									"flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none hover:bg-accent",
									opt.value === operator && "font-medium",
								)}
								onClick={() => {
									handleOperatorChange(opt.value);
									setOperatorOpen(false);
								}}
							>
								<Check
									className={cn(
										"size-4 shrink-0",
										opt.value === operator ? "opacity-100" : "opacity-0",
									)}
								/>
								{opt.label}
							</button>
						))}
					</PopoverContent>
				</Popover>
				<DatePicker>
					<DatePickerTrigger
						className="min-w-0 flex-1 basis-0 !w-auto max-w-full"
						date={currentDate}
						dateFormat="MMM do, yyyy"
						placeholder="Pick a date"
						aria-label={config.label}
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

export function toDate(value: string | undefined): Date | undefined {
	if (!value) return undefined;
	const parsed = parseISO(value);
	return isNaN(parsed.getTime()) ? undefined : parsed;
}

export function toDateString(date: Date | undefined): string {
	if (!date) return "";
	return date.toISOString().split("T")[0];
}
