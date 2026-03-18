import type { ActiveFilter, FilterFieldConfig } from "../lib/listFilters";

const inputClass =
	"h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-purple/20 focus:border-primary-purple";

interface ListPageFiltersProps {
	fieldConfigs: FilterFieldConfig[];
	activeFilters: ActiveFilter[];
	onFiltersChange: (filters: ActiveFilter[]) => void;
}

export function ListPageFilters({
	fieldConfigs,
	activeFilters,
	onFiltersChange,
}: ListPageFiltersProps) {
	const addFilter = () => {
		const first = fieldConfigs[0];
		if (!first) return;
		onFiltersChange([...activeFilters, { fieldKey: first.key, value: "" }]);
	};

	const updateFilter = (index: number, updates: Partial<ActiveFilter>) => {
		const next = [...activeFilters];
		next[index] = { ...next[index]!, ...updates };
		onFiltersChange(next);
	};

	const removeFilter = (index: number) => {
		onFiltersChange(activeFilters.filter((_, i) => i !== index));
	};

	if (fieldConfigs.length === 0) return null;

	return (
		<div className="flex flex-wrap items-center gap-2 mb-4">
			{activeFilters.map((filter, index) => {
				const config = fieldConfigs.find((c) => c.key === filter.fieldKey) ?? fieldConfigs[0]!;
				return (
					<div key={index} className="flex items-center gap-2 flex-wrap">
						<select
							className={inputClass}
							value={filter.fieldKey}
							onChange={(e) => updateFilter(index, { fieldKey: e.target.value })}
							aria-label="Filter field"
						>
							{fieldConfigs.map((c) => (
								<option key={c.key} value={c.key}>
									{c.label}
								</option>
							))}
						</select>
						{config.type === "select" && config.options && config.options.length > 0 ? (
							<select
								className={inputClass}
								value={filter.value}
								onChange={(e) => updateFilter(index, { value: e.target.value })}
								aria-label={`Filter by ${config.label}`}
							>
								<option value="">Any</option>
								{config.options.map((opt) => (
									<option key={opt.value} value={opt.value}>
										{opt.label}
									</option>
								))}
							</select>
						) : (
							<input
								type="text"
								className={inputClass}
								value={filter.value}
								onChange={(e) => updateFilter(index, { value: e.target.value })}
								placeholder={config.label}
								aria-label={`Filter by ${config.label}`}
							/>
						)}
						<button
							type="button"
							onClick={() => removeFilter(index)}
							className="text-gray-500 hover:text-gray-700 text-sm px-1"
							aria-label="Remove filter"
						>
							✕
						</button>
					</div>
				);
			})}
			<button
				type="button"
				onClick={addFilter}
				className="text-sm text-purple-700 hover:text-purple-800 font-medium"
			>
				+ Add filter
			</button>
		</div>
	);
}
