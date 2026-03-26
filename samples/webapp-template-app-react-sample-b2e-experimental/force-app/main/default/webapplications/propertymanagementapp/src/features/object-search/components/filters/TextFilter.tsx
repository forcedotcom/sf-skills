import { Input } from "../../../../components/ui/input";
import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import { useFilterField } from "../FilterContext";
import type { ActiveFilterValue } from "../../utils/filterUtils";

interface TextFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	placeholder?: string;
	helpText?: string;
}

export function TextFilter({
	field,
	label,
	placeholder,
	helpText,
	className,
	...props
}: TextFilterProps) {
	const { value, onChange } = useFilterField(field);
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label htmlFor={`filter-${field}`}>{label}</Label>
			<TextFilterInput
				field={field}
				label={label}
				placeholder={placeholder}
				value={value}
				onChange={onChange}
			/>
			{helpText && <p className="text-xs text-muted-foreground">{helpText}</p>}
		</div>
	);
}

interface TextFilterInputProps extends Omit<
	React.ComponentProps<typeof Input>,
	"onChange" | "value"
> {
	field: string;
	label: string;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
}

export function TextFilterInput({
	field,
	label,
	value,
	onChange,
	className,
	...props
}: TextFilterInputProps) {
	return (
		<Input
			id={`filter-${field}`}
			type="text"
			placeholder={props.placeholder ?? `Filter by ${label.toLowerCase()}...`}
			value={value?.value ?? ""}
			onChange={(e) => {
				const v = e.target.value;
				if (v) {
					onChange({ field, label, type: "text", value: v });
				} else {
					onChange(undefined);
				}
			}}
			className={cn(className)}
			{...props}
		/>
	);
}
