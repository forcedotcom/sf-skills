import type { Filter } from "../../features/global-search/types/filters/filters";
import { FilterFieldRange } from "./FilterFieldRange";
import { FilterFieldSelect } from "./FilterFieldSelect";
import { FilterFieldText } from "./FilterFieldText";

/** Compatible with feature picklist option shape (label/value). */
interface PicklistOption {
	label?: string;
	value: string;
}
interface ListPageFilterRowProps {
	filters: Filter[];
	picklistValues: Record<string, PicklistOption[]>;
	formValues: Record<string, string>;
	onFormValueChange: (key: string, value: string) => void;
	onApply: () => void;
	onReset: () => void;
	ariaLabel?: string;
}

/**
 * Horizontal row of filter controls: range, select (multi-select), and text fields + Apply/Reset.
 */
export function ListPageFilterRow({
	filters,
	picklistValues,
	formValues,
	onFormValueChange,
	onApply,
	onReset,
	ariaLabel = "Filters",
}: ListPageFilterRowProps) {
	if (filters.length === 0) return null;

	return (
		<div
			className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
			role="region"
			aria-label={ariaLabel}
		>
			<div className="flex flex-wrap items-end gap-4">
				{filters.map((filter) => {
					if (!filter?.targetFieldPath) return null;
					const affordance = (filter.affordance ?? "").toLowerCase();

					if (affordance === "range") {
						return (
							<FilterFieldRange
								key={filter.targetFieldPath}
								filter={filter}
								formValues={formValues}
								onChange={onFormValueChange}
							/>
						);
					}

					if (affordance === "select") {
						const options = picklistValues[filter.targetFieldPath] ?? [];
						const value = formValues[filter.targetFieldPath] ?? "";
						return (
							<FilterFieldSelect
								key={filter.targetFieldPath}
								filter={filter}
								options={options}
								value={value}
								onChange={(v) => onFormValueChange(filter.targetFieldPath, v)}
								multiSelect={true}
							/>
						);
					}

					return (
						<FilterFieldText
							key={filter.targetFieldPath}
							filter={filter}
							value={formValues[filter.targetFieldPath] ?? ""}
							onChange={(v) => onFormValueChange(filter.targetFieldPath, v)}
						/>
					);
				})}
				<div className="flex items-center gap-2 ml-2 shrink-0">
					<button
						onClick={onApply}
						className="h-9 px-4 bg-purple-700 hover:bg-purple-800 text-white text-sm font-medium rounded-md"
						aria-label="Apply filters"
					>
						Apply
					</button>
					<button
						onClick={onReset}
						className="h-9 px-4 text-sm font-medium rounded-md border-gray-300"
						aria-label="Reset filters"
					>
						Reset
					</button>
				</div>
			</div>
		</div>
	);
}
