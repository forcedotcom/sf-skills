import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import { useFilterField } from "../FilterContext";
import type { ActiveFilterValue } from "../../utils/filterUtils";

const ALL_VALUE = "__all__";

interface SelectFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	options: Array<{ value: string; label: string }>;
	helpText?: string;
}

export function SelectFilter({
	field,
	label,
	options,
	helpText,
	className,
	...props
}: SelectFilterProps) {
	const { value, onChange } = useFilterField(field);
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label htmlFor={`filter-${field}`}>{label}</Label>
			<SelectFilterControl
				field={field}
				label={label}
				options={options}
				value={value}
				onChange={onChange}
			/>
			{helpText && <p className="text-xs text-muted-foreground">{helpText}</p>}
		</div>
	);
}

interface SelectFilterControlProps {
	field: string;
	label: string;
	options: Array<{ value: string; label: string }>;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	triggerProps?: React.ComponentProps<typeof SelectTrigger>;
	contentProps?: React.ComponentProps<typeof SelectContent>;
}

export function SelectFilterControl({
	field,
	label,
	options,
	value,
	onChange,
	triggerProps,
	contentProps,
}: SelectFilterControlProps) {
	return (
		<Select
			value={value?.value ?? ALL_VALUE}
			onValueChange={(v) => {
				if (v === ALL_VALUE) {
					onChange(undefined);
				} else {
					onChange({ field, label, type: "picklist", value: v });
				}
			}}
		>
			<SelectTrigger
				id={`filter-${field}`}
				{...triggerProps}
				className={cn("w-full", triggerProps?.className)}
			>
				<SelectValue placeholder={`Select ${label.toLowerCase()}`} />
			</SelectTrigger>
			<SelectContent {...contentProps}>
				<SelectItem value={ALL_VALUE}>All</SelectItem>
				{options.map((opt) => (
					<SelectItem key={opt.value} value={opt.value}>
						{opt.label}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}
