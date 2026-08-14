import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../../components/ui/select";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";

const ALL_VALUE = "__all__";

interface SelectFilterProps {
	field: string;
	label: string;
	options: Array<{ value: string; label: string }>;
	helpText?: string;
}

export function SelectFilter({ field, label, options, helpText }: SelectFilterProps) {
	const { value, onChange } = useFilterField(field);
	const id = `filter-${field}`;
	return (
		<FilterFieldWrapper label={label} htmlFor={id} helpText={helpText}>
			<Select
				value={value?.value ?? ALL_VALUE}
				onValueChange={(v) => {
					if (v === ALL_VALUE) onChange(undefined);
					else onChange({ field, label, type: "picklist", value: v });
				}}
			>
				<SelectTrigger id={id} className="w-full">
					<SelectValue placeholder={`Select ${label.toLowerCase()}`} />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={ALL_VALUE}>All</SelectItem>
					{options.map((opt) => (
						<SelectItem key={opt.value} value={opt.value}>
							{opt.label}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
		</FilterFieldWrapper>
	);
}
