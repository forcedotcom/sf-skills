/**
 * Horizontal filter row for object-search pages.
 * Filter changes are held in local draft state; the API is only triggered when
 * the user clicks Apply. Reset clears filters and draft.
 */
import { useState, useEffect, useRef } from "react";
import type { ActiveFilterValue, FilterFieldConfig } from "../utils/filterUtils";
import { TextFilter } from "./filters/TextFilter";
import { SearchFilter } from "./filters/SearchFilter";
import { DateFilter } from "./filters/DateFilter";
import { NumericRangeFilter } from "./filters/NumericRangeFilter";
import { MultiSelectFilter } from "./filters/MultiSelectFilter";

interface PicklistOption {
	value: string;
	label: string;
}

export interface ObjectSearchFilterRowProps {
	configs: FilterFieldConfig[];
	/** Applied filters from useObjectSearchParams (filters.active). Used to initialize and sync draft. */
	activeFilters: ActiveFilterValue[];
	onFilterChange: (field: string, value: ActiveFilterValue | undefined) => void;
	onFilterRemove: (field: string) => void;
	onReset: () => void;
	ariaLabel?: string;
}

function getActiveValueForField(
	activeFilters: ActiveFilterValue[],
	field: string,
): ActiveFilterValue | undefined {
	return activeFilters.find((x) => x.field === field);
}

export function ObjectSearchFilterRow({
	configs,
	activeFilters,
	onFilterChange,
	onFilterRemove,
	onReset,
	ariaLabel = "Filters",
}: ObjectSearchFilterRowProps) {
	const [draftFilters, setDraftFilters] = useState<ActiveFilterValue[]>(() => activeFilters);
	const applyingRef = useRef(false);

	// Sync draft from parent when applied filters change (e.g. after Reset or external URL change).
	// Skip during Apply to avoid overwriting draft with intermediate state.
	useEffect(() => {
		if (!applyingRef.current) {
			setDraftFilters(activeFilters);
		}
	}, [activeFilters]);

	const handleApply = () => {
		applyingRef.current = true;
		configs.forEach((config) => {
			const field = (config as { field?: string }).field;
			if (!field) return;
			const value = getActiveValueForField(draftFilters, field);
			if (value) {
				onFilterChange(field, value);
			} else {
				onFilterRemove(field);
			}
		});
		setTimeout(() => {
			applyingRef.current = false;
		}, 0);
	};

	const handleReset = () => {
		onReset();
		setDraftFilters([]);
	};

	const handleDraftChange = (field: string, value: ActiveFilterValue | undefined) => {
		setDraftFilters((prev) => {
			const next = prev.filter((f) => f.field !== field);
			if (value) next.push(value);
			return next;
		});
	};

	if (configs.length === 0) return null;

	return (
		<div
			className="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
			role="region"
			aria-label={ariaLabel}
		>
			<div className="flex flex-wrap items-end gap-4">
				{configs.map((config) => {
					const field = (config as { field?: string }).field;
					const type = ((config as { type?: string }).type ?? "text") as string;
					const options = (config as { options?: PicklistOption[] }).options ?? [];

					if (!field) return null;

					const effectiveConfig = {
						...config,
						options:
							options.length > 0 ? options : (config as { options?: PicklistOption[] }).options,
					} as FilterFieldConfig;

					const value = getActiveValueForField(draftFilters, field);
					const handleChange = (v: ActiveFilterValue | undefined) => handleDraftChange(field, v);

					const wrapperClass = "flex flex-col gap-1 min-w-[140px]";

					if (type === "multipicklist" || type === "picklist") {
						return (
							<div key={field} className={wrapperClass}>
								<MultiSelectFilter
									config={effectiveConfig}
									value={value}
									onChange={handleChange}
									className="min-w-[140px]"
								/>
							</div>
						);
					}

					if (type === "numeric") {
						return (
							<div key={field} className={`${wrapperClass} min-w-[160px]`}>
								<NumericRangeFilter
									config={effectiveConfig}
									value={value}
									onChange={handleChange}
								/>
							</div>
						);
					}

					if (type === "date") {
						return (
							<div key={field} className={`${wrapperClass} min-w-0`}>
								<DateFilter config={effectiveConfig} value={value} onChange={handleChange} />
							</div>
						);
					}

					if (type === "search") {
						return (
							<div key={field} className={`${wrapperClass} min-w-[180px]`}>
								<SearchFilter config={effectiveConfig} value={value} onChange={handleChange} />
							</div>
						);
					}

					return (
						<div key={field} className={`${wrapperClass} min-w-[180px]`}>
							<TextFilter config={effectiveConfig} value={value} onChange={handleChange} />
						</div>
					);
				})}
				<div className="flex items-center gap-2 ml-2 shrink-0">
					<button
						type="button"
						onClick={handleApply}
						className="h-9 px-4 text-sm font-medium rounded-md bg-purple-700 text-white hover:bg-purple-800"
						aria-label="Apply filters"
					>
						Apply
					</button>
					<button
						type="button"
						onClick={handleReset}
						className="h-9 px-4 text-sm font-medium rounded-md border border-gray-300 hover:bg-gray-50"
						aria-label="Reset filters"
					>
						Reset
					</button>
				</div>
			</div>
		</div>
	);
}
