import { Input } from "../../../../components/ui/input";
import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import type { FilterFieldConfig, ActiveFilterValue } from "../../utils/filterUtils";

interface NumericRangeFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	labelProps?: React.ComponentProps<typeof Label>;
	controlProps?: Omit<
		React.ComponentProps<typeof NumericRangeFilterInputs>,
		"config" | "value" | "onChange"
	>;
	helpTextProps?: React.ComponentProps<"p">;
}

export function NumericRangeFilter({
	config,
	value,
	onChange,
	className,
	labelProps,
	controlProps,
	helpTextProps,
	...props
}: NumericRangeFilterProps) {
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label {...labelProps}>{labelProps?.children ?? config.label}</Label>
			<NumericRangeFilterInputs
				config={config}
				value={value}
				onChange={onChange}
				{...controlProps}
			/>
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

interface NumericRangeFilterInputsProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	minInputProps?: React.ComponentProps<typeof Input>;
	maxInputProps?: React.ComponentProps<typeof Input>;
}

export function NumericRangeFilterInputs({
	config,
	value,
	onChange,
	className,
	minInputProps,
	maxInputProps,
	...props
}: NumericRangeFilterInputsProps) {
	const handleChange = (field: "min" | "max", v: string) => {
		const next = {
			field: config.field,
			label: config.label,
			type: "numeric" as const,
			min: value?.min ?? "",
			max: value?.max ?? "",
			[field]: v,
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
				aria-label={`${config.label} minimum`}
				{...minInputProps}
			/>
			<Input
				type="number"
				placeholder="Max"
				value={value?.max ?? ""}
				onChange={(e) => handleChange("max", e.target.value)}
				aria-label={`${config.label} maximum`}
				{...maxInputProps}
			/>
		</div>
	);
}
