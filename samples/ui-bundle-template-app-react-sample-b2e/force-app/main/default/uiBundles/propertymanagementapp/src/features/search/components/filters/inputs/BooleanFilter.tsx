import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../../components/ui/select";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";

const ANY_VALUE = "__any__";

interface BooleanFilterProps {
	field: string;
	label: string;
	trueLabel?: string;
	falseLabel?: string;
	helpText?: string;
}

export function BooleanFilter({
	field,
	label,
	trueLabel = "Yes",
	falseLabel = "No",
	helpText,
}: BooleanFilterProps) {
	const { value, onChange } = useFilterField(field);
	const id = `filter-${field}`;
	return (
		<FilterFieldWrapper label={label} htmlFor={id} helpText={helpText}>
			<Select
				value={value?.value ?? ANY_VALUE}
				onValueChange={(v) => {
					if (v === ANY_VALUE) onChange(undefined);
					else onChange({ field, label, type: "boolean", value: v });
				}}
			>
				<SelectTrigger id={id} className="w-full">
					<SelectValue />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={ANY_VALUE}>Any</SelectItem>
					<SelectItem value="true">{trueLabel}</SelectItem>
					<SelectItem value="false">{falseLabel}</SelectItem>
				</SelectContent>
			</Select>
		</FilterFieldWrapper>
	);
}
