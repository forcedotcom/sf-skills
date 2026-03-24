import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import type { FilterFieldConfig, ActiveFilterValue } from "../../utils/filterUtils";

const ALL_VALUE = "__all__";

interface BooleanFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	labelProps?: React.ComponentProps<typeof Label>;
	controlProps?: Omit<
		React.ComponentProps<typeof BooleanFilterSelect>,
		"config" | "value" | "onChange"
	>;
	helpTextProps?: React.ComponentProps<"p">;
}

export function BooleanFilter({
	config,
	value,
	onChange,
	className,
	labelProps,
	controlProps,
	helpTextProps,
	...props
}: BooleanFilterProps) {
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label htmlFor={`filter-${config.field}`} {...labelProps}>
				{labelProps?.children ?? config.label}
			</Label>
			<BooleanFilterSelect config={config} value={value} onChange={onChange} {...controlProps} />
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

interface BooleanFilterSelectProps {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	triggerProps?: React.ComponentProps<typeof SelectTrigger>;
	contentProps?: React.ComponentProps<typeof SelectContent>;
}

export function BooleanFilterSelect({
	config,
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
					onChange({ field: config.field, label: config.label, type: "boolean", value: v });
				}
			}}
		>
			<SelectTrigger
				id={`filter-${config.field}`}
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
