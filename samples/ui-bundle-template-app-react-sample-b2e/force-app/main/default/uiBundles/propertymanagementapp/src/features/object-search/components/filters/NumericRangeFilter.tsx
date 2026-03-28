import { Input } from "../../../../components/ui/input";
import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import { useFilterField } from "../FilterContext";
import type { ActiveFilterValue } from "../../utils/filterUtils";

interface NumericRangeFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	helpText?: string;
}

export function NumericRangeFilter({
	field,
	label,
	helpText,
	className,
	...props
}: NumericRangeFilterProps) {
	const { value, onChange } = useFilterField(field);
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label>{label}</Label>
			<NumericRangeFilterInputs field={field} label={label} value={value} onChange={onChange} />
			{helpText && <p className="text-xs text-muted-foreground">{helpText}</p>}
		</div>
	);
}

interface NumericRangeFilterInputsProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	minInputProps?: React.ComponentProps<typeof Input>;
	maxInputProps?: React.ComponentProps<typeof Input>;
}

export function NumericRangeFilterInputs({
	field,
	label,
	value,
	onChange,
	className,
	minInputProps,
	maxInputProps,
	...props
}: NumericRangeFilterInputsProps) {
	const handleChange = (bound: "min" | "max", v: string) => {
		const next = {
			field,
			label,
			type: "numeric" as const,
			min: value?.min ?? "",
			max: value?.max ?? "",
			[bound]: v,
		};
		if (!next.min && !next.max) {
			onChange(undefined);
		} else {
			onChange(next);
		}
	};

	return (
		<div className={cn("flex gap-2", className)} {...props}>
			<Input
				type="number"
				placeholder="Min"
				value={value?.min ?? ""}
				onChange={(e) => handleChange("min", e.target.value)}
				aria-label={`${label} minimum`}
				{...minInputProps}
			/>
			<Input
				type="number"
				placeholder="Max"
				value={value?.max ?? ""}
				onChange={(e) => handleChange("max", e.target.value)}
				aria-label={`${label} maximum`}
				{...maxInputProps}
			/>
		</div>
	);
}
