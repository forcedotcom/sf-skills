import { useState, useCallback } from "react";
import { type FilterCriteria } from "../features/global-search/types/filters/filters";
import { useObjectListMetadata } from "../features/global-search/hooks/useObjectSearchData";
import { parseFilterValue } from "../features/global-search/utils/filterUtils";
import { sanitizeFilterValue } from "../features/global-search/utils/sanitizationUtils";

const inputClass =
	"h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-purple/20 focus:border-primary-purple";

interface FiltersFromApiProps {
	objectApiName: string | null;
	onApplyFilters: (criteria: FilterCriteria[]) => void;
}

/**
 * Renders filter UI from the react-global-search filters API (getObjectListFilters).
 * Uses useObjectListMetadata to load filters and picklist values, then builds FilterCriteria on Apply.
 */
export function FiltersFromApi({ objectApiName, onApplyFilters }: FiltersFromApiProps) {
	const { filters, picklistValues, loading, error } = useObjectListMetadata(objectApiName);
	const [formValues, setFormValues] = useState<Record<string, string>>({});
	const [rangeMin, setRangeMin] = useState<Record<string, string>>({});
	const [rangeMax, setRangeMax] = useState<Record<string, string>>({});

	const handleChange = useCallback((fieldPath: string, value: string) => {
		setFormValues((prev) => ({ ...prev, [fieldPath]: value }));
	}, []);

	const handleRangeChange = useCallback((fieldPath: string, min: string, max: string) => {
		setRangeMin((prev) => ({ ...prev, [fieldPath]: min }));
		setRangeMax((prev) => ({ ...prev, [fieldPath]: max }));
	}, []);

	const handleApply = useCallback(() => {
		if (!objectApiName || !filters?.length) {
			onApplyFilters([]);
			return;
		}
		const criteria: FilterCriteria[] = [];
		for (const filter of filters) {
			if (!filter?.targetFieldPath) continue;
			const affordance = (filter.affordance ?? "").toLowerCase();
			if (affordance === "range") {
				const minVal = sanitizeFilterValue(rangeMin[filter.targetFieldPath] ?? "");
				const maxVal = sanitizeFilterValue(rangeMax[filter.targetFieldPath] ?? "");
				if (minVal) {
					const parsed = parseFilterValue(minVal);
					if (parsed !== "")
						criteria.push({
							objectApiName,
							fieldPath: filter.targetFieldPath,
							operator: "gte",
							values: [parsed],
						});
				}
				if (maxVal) {
					const parsed = parseFilterValue(maxVal);
					if (parsed !== "")
						criteria.push({
							objectApiName,
							fieldPath: filter.targetFieldPath,
							operator: "lte",
							values: [parsed],
						});
				}
			} else {
				const raw = formValues[filter.targetFieldPath] ?? "";
				const fieldValue = sanitizeFilterValue(raw);
				if (!fieldValue) continue;
				if (affordance === "select") {
					criteria.push({
						objectApiName,
						fieldPath: filter.targetFieldPath,
						operator: "eq",
						values: [fieldValue],
					});
				} else {
					criteria.push({
						objectApiName,
						fieldPath: filter.targetFieldPath,
						operator: "like",
						values: [`%${fieldValue}%`],
					});
				}
			}
		}
		onApplyFilters(criteria);
	}, [objectApiName, filters, formValues, rangeMin, rangeMax, onApplyFilters]);

	const handleReset = useCallback(() => {
		setFormValues({});
		setRangeMin({});
		setRangeMax({});
		onApplyFilters([]);
	}, [onApplyFilters]);

	if (!objectApiName) return null;
	if (loading) {
		return (
			<div className="mb-4 flex flex-wrap gap-2 items-center text-sm text-gray-500">
				Loading filters…
			</div>
		);
	}
	if (error || !filters?.length) return null;

	return (
		<div className="mb-4 flex flex-wrap items-end gap-3">
			{filters.map((filter) => {
				if (!filter.targetFieldPath) return null;
				const affordance = (filter.affordance ?? "").toLowerCase();
				if (affordance === "range") {
					return (
						<div key={filter.targetFieldPath} className="flex items-center gap-2 flex-wrap">
							<span className="text-sm text-gray-600">{filter.label}</span>
							<input
								type="text"
								className={inputClass}
								placeholder="Min"
								value={rangeMin[filter.targetFieldPath] ?? ""}
								onChange={(e) =>
									handleRangeChange(
										filter.targetFieldPath,
										e.target.value,
										rangeMax[filter.targetFieldPath] ?? "",
									)
								}
								aria-label={`${filter.label} min`}
							/>
							<input
								type="text"
								className={inputClass}
								placeholder="Max"
								value={rangeMax[filter.targetFieldPath] ?? ""}
								onChange={(e) =>
									handleRangeChange(
										filter.targetFieldPath,
										rangeMin[filter.targetFieldPath] ?? "",
										e.target.value,
									)
								}
								aria-label={`${filter.label} max`}
							/>
						</div>
					);
				}
				if (affordance === "select") {
					const options = picklistValues?.[filter.targetFieldPath] ?? [];
					return (
						<div key={filter.targetFieldPath} className="flex items-center gap-2">
							<label className="text-sm text-gray-600">{filter.label}</label>
							<select
								className={inputClass}
								value={formValues[filter.targetFieldPath] ?? ""}
								onChange={(e) => handleChange(filter.targetFieldPath, e.target.value)}
								aria-label={filter.label}
							>
								<option value="">Any</option>
								{options.map((opt) => (
									<option key={opt.value} value={opt.value}>
										{opt.label}
									</option>
								))}
							</select>
						</div>
					);
				}
				return (
					<div key={filter.targetFieldPath} className="flex items-center gap-2">
						<label className="text-sm text-gray-600">{filter.label}</label>
						<input
							type="text"
							className={inputClass}
							placeholder={filter.attributes?.placeholder ?? filter.label}
							value={formValues[filter.targetFieldPath] ?? ""}
							onChange={(e) => handleChange(filter.targetFieldPath, e.target.value)}
							aria-label={filter.label}
						/>
					</div>
				);
			})}
			<button
				type="button"
				onClick={handleApply}
				className="h-9 px-3 rounded-md bg-purple-700 text-white text-sm font-medium hover:bg-purple-800"
			>
				Apply Filters
			</button>
			<button
				type="button"
				onClick={handleReset}
				className="h-9 px-3 text-sm text-gray-600 hover:text-gray-800"
			>
				Reset
			</button>
		</div>
	);
}
