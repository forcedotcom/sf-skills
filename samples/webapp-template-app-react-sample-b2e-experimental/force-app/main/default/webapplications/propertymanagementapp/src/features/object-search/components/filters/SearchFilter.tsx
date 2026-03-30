import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import { SearchBar } from "../SearchBar";
import { useFilterField } from "../FilterContext";

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
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label htmlFor={`filter-${field}`}>{label}</Label>
			<SearchBar
				value={value?.value ?? ""}
				handleChange={(v) => {
					if (v) {
						onChange({ field, label, type: "search", value: v });
					} else {
						onChange(undefined);
					}
				}}
				placeholder={placeholder}
				inputProps={{ id: `filter-${field}` }}
			/>
		</div>
	);
}
