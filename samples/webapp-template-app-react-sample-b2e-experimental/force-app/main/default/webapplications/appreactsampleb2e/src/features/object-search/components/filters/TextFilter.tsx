import { Input } from "../../../../components/ui/input";
import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import type { FilterFieldConfig, ActiveFilterValue } from "../../utils/filterUtils";

interface TextFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	labelProps?: React.ComponentProps<typeof Label>;
	inputProps?: Omit<React.ComponentProps<typeof TextFilterInput>, "config" | "value" | "onChange">;
	helpTextProps?: React.ComponentProps<"p">;
}

export function TextFilter({
	config,
	value,
	onChange,
	className,
	labelProps,
	inputProps,
	helpTextProps,
	...props
}: TextFilterProps) {
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label htmlFor={`filter-${config.field}`} {...labelProps}>
				{labelProps?.children ?? config.label}
			</Label>
			<TextFilterInput config={config} value={value} onChange={onChange} {...inputProps} />
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

interface TextFilterInputProps extends Omit<
	React.ComponentProps<typeof Input>,
	"onChange" | "value"
> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
}

export function TextFilterInput({
	config,
	value,
	onChange,
	className,
	...props
}: TextFilterInputProps) {
	return (
		<Input
			id={`filter-${config.field}`}
			type="text"
			placeholder={config.placeholder ?? `Filter by ${config.label.toLowerCase()}...`}
			value={value?.value ?? ""}
			onChange={(e) => {
				const v = e.target.value;
				if (v) {
					onChange({ field: config.field, label: config.label, type: "text", value: v });
				} else {
					onChange(undefined);
				}
			}}
			className={cn(className)}
			{...props}
		/>
	);
}
