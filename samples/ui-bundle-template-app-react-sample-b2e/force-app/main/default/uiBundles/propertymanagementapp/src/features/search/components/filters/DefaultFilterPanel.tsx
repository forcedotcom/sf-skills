/**
 * Default filter panel used when no `renderFilters` is supplied for a source.
 *
 * Renders one input per entry in `source.filterBy`, picking the right
 * component for each `FilterFieldType`:
 *
 *   - text                                  → TextFilter
 *   - picklist                              → SelectFilter (inline options or auto-fetched)
 *   - multipicklist                         → MultiSelectFilter (inline options or auto-fetched)
 *   - numeric                               → NumericRangeFilter
 *   - boolean                               → BooleanFilter
 *   - date / daterange / datetime / datetimerange → DateRangeFilter
 *       (its Between / After / Before chrome is chosen by `filter.dateMode`)
 *
 * Applications can still pass `renderFilters[sourceKey]` to override the
 * entire panel for a specific source.
 */

import { TextFilter } from "./inputs/TextFilter";
import { SelectFilter } from "./inputs/SelectFilter";
import { MultiSelectFilter } from "./inputs/MultiSelectFilter";
import { NumericRangeFilter } from "./inputs/NumericRangeFilter";
import { BooleanFilter } from "./inputs/BooleanFilter";
import { DateRangeFilter } from "./inputs/DateRangeFilter";
import { useDistinctValues } from "../../hooks/useDistinctValues";
import type { FilterFieldConfig } from "../../utils/filterUtils";
import type { SObjectSourceConfig } from "../../types";

interface DefaultFilterPanelProps {
	source: SObjectSourceConfig;
}

export function DefaultFilterPanel({ source }: DefaultFilterPanelProps) {
	const filters = source.filterBy ?? [];
	if (filters.length === 0) return null;
	return (
		<>
			{filters.map((filter) => (
				<DefaultFilterField key={filter.field} filter={filter} source={source} />
			))}
		</>
	);
}

interface DefaultFilterFieldProps {
	filter: FilterFieldConfig;
	source: SObjectSourceConfig;
}

function DefaultFilterField({ filter, source }: DefaultFilterFieldProps) {
	switch (filter.type) {
		case "text":
			return (
				<TextFilter
					field={filter.field}
					label={filter.label}
					placeholder={filter.placeholder}
					helpText={filter.helpText}
				/>
			);
		case "picklist":
			return <PicklistField filter={filter} source={source} multi={false} />;
		case "multipicklist":
			return <PicklistField filter={filter} source={source} multi={true} />;
		case "numeric":
			return (
				<NumericRangeFilter
					field={filter.field}
					label={filter.label}
					helpText={filter.helpText}
					min={filter.min}
					max={filter.max}
				/>
			);
		case "boolean":
			return <BooleanFilter field={filter.field} label={filter.label} helpText={filter.helpText} />;
		case "date":
		case "daterange":
			return (
				<DateRangeFilter
					field={filter.field}
					label={filter.label}
					helpText={filter.helpText}
					filterType="daterange"
					mode={filter.dateMode}
				/>
			);
		case "datetime":
		case "datetimerange":
			return (
				<DateRangeFilter
					field={filter.field}
					label={filter.label}
					helpText={filter.helpText}
					filterType="datetimerange"
					mode={filter.dateMode}
				/>
			);
		default:
			return null;
	}
}

/**
 * Resolves picklist options from inline config first; falls back to fetching
 * distinct values from the GraphQL aggregate API on first render.
 */
function PicklistField({
	filter,
	source,
	multi,
}: {
	filter: FilterFieldConfig;
	source: SObjectSourceConfig;
	multi: boolean;
}) {
	const inline = filter.options;
	const fetched = useDistinctValues(
		inline ? null : { objectName: source.objectName, fieldName: filter.field },
	);
	const options = inline ?? fetched ?? [];
	const Component = multi ? MultiSelectFilter : SelectFilter;
	return (
		<Component
			field={filter.field}
			label={filter.label}
			options={options}
			helpText={filter.helpText}
		/>
	);
}
