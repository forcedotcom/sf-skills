/**
 * FilterSelect Component
 *
 * Renders a dropdown select field for filter values with picklist options.
 * Used for filters with affordance === 'select'.
 *
 * @param filter - Filter definition containing field path, label, and attributes
 * @param value - Currently selected filter value
 * @param options - Array of picklist values to display as options
 * @param onChange - Callback when selection changes
 *
 * @remarks
 * - Filters out invalid options (null/undefined values)
 * - Displays option label if available, otherwise uses value
 * - Shows placeholder from filter attributes or default "Select..."
 *
 * @example
 * ```tsx
 * <FilterSelect
 *   filter={selectFilter}
 *   value={selectedValue}
 *   options={picklistOptions}
 *   onChange={(value) => setSelectedValue(value)}
 * />
 * ```
 */
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { Field, FieldLabel, FieldDescription } from "../../../../components/ui/field";
import type { Filter } from "../../types/filters/filters";
import type { PicklistValue } from "../../types/filters/picklist";

interface FilterSelectProps {
	filter: Filter;
	value: string;
	options: PicklistValue[];
	onChange: (value: string) => void;
}

export default function FilterSelect({ filter, value, options, onChange }: FilterSelectProps) {
	return (
		<Field>
			<FieldLabel htmlFor={filter.targetFieldPath}>
				{filter.label || filter.targetFieldPath}
			</FieldLabel>
			<Select value={value} onValueChange={onChange}>
				<SelectTrigger
					id={filter.targetFieldPath}
					aria-label={filter.label || filter.targetFieldPath}
				>
					<SelectValue placeholder={filter.attributes?.placeholder || "Select..."} />
				</SelectTrigger>
				<SelectContent>
					{options.map((option) => {
						if (!option || !option.value) return null;
						return (
							<SelectItem key={option.value} value={option.value}>
								{option.label || option.value}
							</SelectItem>
						);
					})}
				</SelectContent>
			</Select>
			{filter.helpMessage && <FieldDescription>{filter.helpMessage}</FieldDescription>}
		</Field>
	);
}
