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

interface BooleanFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	helpText?: string;
}

export function BooleanFilter({ field, label, helpText, className, ...props }: BooleanFilterProps) {
	const { value, onChange } = useFilterField(field);
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label htmlFor={`filter-${field}`}>{label}</Label>
			<BooleanFilterSelect field={field} label={label} value={value} onChange={onChange} />
			{helpText && <p className="text-xs text-muted-foreground">{helpText}</p>}
		</div>
	);
}

interface BooleanFilterSelectProps {
	field: string;
	label: string;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	triggerProps?: React.ComponentProps<typeof SelectTrigger>;
	contentProps?: React.ComponentProps<typeof SelectContent>;
}

export function BooleanFilterSelect({
	field,
	label,
	value,
	onChange,
	triggerProps,
	contentProps,
}: BooleanFilterSelectProps) {
	return (
		<Select
			value={value?.value ?? ALL_VALUE}
			onValueChange={(v) => {
				if (v === ALL_VALUE) {
					onChange(undefined);
				} else {
					onChange({ field, label, type: "boolean", value: v });
				}
			}}
		>
			<SelectTrigger
				id={`filter-${field}`}
				{...triggerProps}
				className={cn("w-full", triggerProps?.className)}
			>
				<SelectValue />
			</SelectTrigger>
			<SelectContent {...contentProps}>
				<SelectItem value={ALL_VALUE}>All</SelectItem>
				<SelectItem value="true">Yes</SelectItem>
				<SelectItem value="false">No</SelectItem>
			</SelectContent>
		</Select>
	);
}
