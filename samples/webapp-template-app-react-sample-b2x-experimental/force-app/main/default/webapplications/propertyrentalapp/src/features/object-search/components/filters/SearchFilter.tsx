import { useEffect, useState } from "react";

import { SearchBar } from "../SearchBar";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import { useDebouncedCallback } from "../../hooks/useDebouncedCallback";

interface SearchFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	placeholder?: string;
}

export function SearchFilter({
	field,
	label,
	placeholder,
	className,
	...props
}: SearchFilterProps) {
	const { value, onChange } = useFilterField(field);
	const [localValue, setLocalValue] = useState(value?.value ?? "");

	const externalValue = value?.value ?? "";
	useEffect(() => {
		setLocalValue(externalValue);
	}, [externalValue]);

	const debouncedOnChange = useDebouncedCallback((v: string) => {
		if (v) {
			onChange({ field, label, type: "search", value: v });
		} else {
			onChange(undefined);
		}
	});

	return (
		<FilterFieldWrapper label={label} htmlFor={`filter-${field}`} className={className} {...props}>
			<SearchBar
				value={localValue}
				handleChange={(v) => {
					setLocalValue(v);
					debouncedOnChange(v);
				}}
				placeholder={placeholder}
				inputProps={{ id: `filter-${field}` }}
			/>
		</FilterFieldWrapper>
	);
}
