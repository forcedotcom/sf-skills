import { useEffect, useState } from "react";
import { Input } from "../../../../components/ui/input";
import { cn } from "../../../../lib/utils";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import { useDebouncedCallback } from "../../hooks/useDebouncedCallback";
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
		<FilterFieldWrapper
			label={label}
			htmlFor={`filter-${field}`}
			helpText={helpText}
			className={className}
			{...props}
		>
			<TextFilterInput
				field={field}
				label={label}
				placeholder={placeholder}
				value={value}
				onChange={onChange}
			/>
		</FilterFieldWrapper>
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
	const [localValue, setLocalValue] = useState(value?.value ?? "");

	const externalValue = value?.value ?? "";
	useEffect(() => {
		setLocalValue(externalValue);
	}, [externalValue]);

	const debouncedOnChange = useDebouncedCallback((v: string) => {
		if (v) {
			onChange({ field, label, type: "text", value: v });
		} else {
			onChange(undefined);
		}
	});

	return (
		<Input
			id={`filter-${field}`}
			type="text"
			placeholder={props.placeholder ?? `Filter by ${label.toLowerCase()}...`}
			value={localValue}
			onChange={(e) => {
				setLocalValue(e.target.value);
				debouncedOnChange(e.target.value);
			}}
			className={cn(className)}
			{...props}
		/>
	);
}
