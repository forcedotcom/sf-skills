/**
 * FilterInput Component
 *
 * Renders a text input field for filter values.
 * Used for filters that don't have a picklist (affordance !== 'select').
 *
 * @param filter - Filter definition containing field path, label, and attributes
 * @param value - Current filter input value
 * @param onChange - Callback when input value changes
 *
 * @remarks
 * - Displays filter label or field path as the label
 * - Shows placeholder text from filter attributes or generates default
 * - Displays help message if available
 *
 * @example
 * ```tsx
 * <FilterInput
 *   filter={textFilter}
 *   value={filterValue}
 *   onChange={(value) => setFilterValue(value)}
 * />
 * ```
 */
import { Input } from "../../../components/ui/input";
import { Field, FieldLabel, FieldDescription } from "../../../components/ui/field";
import type { Filter } from "../types/filters/filters";

interface FilterInputProps {
	filter: Filter;
	value: string;
	onChange: (value: string) => void;
}

export default function FilterInput({ filter, value, onChange }: FilterInputProps) {
	return (
		<Field>
			<FieldLabel htmlFor={filter.targetFieldPath}>
				{filter.label || filter.targetFieldPath}
			</FieldLabel>
			<Input
				id={filter.targetFieldPath}
				type="text"
				value={value}
				onChange={(e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
				placeholder={
					filter.attributes?.placeholder ||
					`Enter ${(filter.label || filter.targetFieldPath).toLowerCase()}`
				}
				aria-label={filter.label || filter.targetFieldPath}
			/>
			{filter.helpMessage && <FieldDescription>{filter.helpMessage}</FieldDescription>}
		</Field>
	);
}
