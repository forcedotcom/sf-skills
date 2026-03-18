/**
 * FilterField Component
 *
 * Wrapper component that renders the appropriate filter input type based on filter affordance.
 * Routes to FilterInput for text fields or FilterSelect for picklist fields.
 *
 * @param filter - Filter definition containing field path, label, and affordance
 * @param value - Current filter value
 * @param picklistValues - Array of picklist options (for select fields)
 * @param onChange - Callback when filter value changes
 *
 * @remarks
 * - Automatically determines input type from filter.affordance
 * - Returns null if filter is invalid
 * - Defaults to text input if affordance is not 'select'
 *
 * @example
 * ```tsx
 * <FilterField
 *   filter={filter}
 *   value={filterValue}
 *   picklistValues={picklistOptions}
 *   onChange={(value) => setFilterValue(value)}
 * />
 * ```
 */
import FilterInput from "./FilterInput";
import FilterSelect from "./FilterSelect";
import type { Filter } from "../../types/filters/filters";
import type { PicklistValue } from "../../types/filters/picklist";

interface FilterFieldProps {
	filter: Filter;
	value: string;
	picklistValues: PicklistValue[];
	onChange: (value: string) => void;
}

export default function FilterField({ filter, value, picklistValues, onChange }: FilterFieldProps) {
	// Guard against invalid filter objects
	if (!filter || !filter.targetFieldPath) {
		return null;
	}

	const affordance = filter.affordance?.toLowerCase() || "";

	if (affordance === "select") {
		const options = picklistValues || [];
		return <FilterSelect filter={filter} value={value} options={options} onChange={onChange} />;
	}

	// Default to text input
	return <FilterInput filter={filter} value={value} onChange={onChange} />;
}
