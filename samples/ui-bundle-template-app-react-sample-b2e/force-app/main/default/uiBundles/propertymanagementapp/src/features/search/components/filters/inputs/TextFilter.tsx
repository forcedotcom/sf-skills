import { useEffect, useRef, useState } from "react";
import { Input } from "../../../../../components/ui/input";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import { debounce, FILTER_DEBOUNCE_MS } from "../../../utils/debounce";

interface TextFilterProps {
	field: string;
	label: string;
	placeholder?: string;
	helpText?: string;
}

export function TextFilter({ field, label, placeholder, helpText }: TextFilterProps) {
	const { value, onChange } = useFilterField(field);
	const [draft, setDraft] = useState(value?.value ?? "");

	const onChangeRef = useRef(onChange);
	useEffect(() => {
		onChangeRef.current = onChange;
	});
	// Build the debounced caller in a mount effect, not during render: creating it
	// inline would read onChangeRef.current at render time (react-hooks/refs). It
	// stays a single stable instance and always calls the latest onChange via the ref.
	const debouncedRef = useRef<((next: string) => void) | undefined>(undefined);
	useEffect(() => {
		debouncedRef.current = debounce((next: string) => {
			if (next === "") onChangeRef.current(undefined);
			else onChangeRef.current({ field, label, type: "text", value: next });
		}, FILTER_DEBOUNCE_MS);
	}, [field, label]);

	useEffect(() => {
		setDraft(value?.value ?? "");
	}, [value?.value]);

	const id = `filter-${field}`;
	return (
		<FilterFieldWrapper label={label} htmlFor={id} helpText={helpText}>
			<Input
				id={id}
				type="text"
				value={draft}
				placeholder={placeholder}
				onChange={(e) => {
					setDraft(e.target.value);
					debouncedRef.current?.(e.target.value);
				}}
			/>
		</FilterFieldWrapper>
	);
}
