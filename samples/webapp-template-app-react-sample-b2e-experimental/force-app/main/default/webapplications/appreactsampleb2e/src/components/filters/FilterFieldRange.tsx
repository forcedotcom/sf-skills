import type { Filter } from "../../features/global-search/types/filters/filters";
import { getRangeMinKey, getRangeMaxKey } from "../../lib/filterUtils";

const inputClass =
	"h-9 px-3 rounded-md border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent w-20";

interface FilterFieldRangeProps {
	filter: Filter;
	formValues: Record<string, string>;
	onChange: (key: string, value: string) => void;
}

export function FilterFieldRange({ filter, formValues, onChange }: FilterFieldRangeProps) {
	const label = filter.label || filter.targetFieldPath;
	const minKey = getRangeMinKey(filter.targetFieldPath);
	const maxKey = getRangeMaxKey(filter.targetFieldPath);
	return (
		<div className="flex flex-col gap-1.5 min-w-[140px]" role="group" aria-label={label + " range"}>
			<label className="text-sm font-medium text-gray-700 whitespace-nowrap">{label}</label>
			<div className="flex gap-2">
				<input
					type="text"
					value={formValues[minKey] ?? ""}
					onChange={(e) => onChange(minKey, e.target.value)}
					placeholder="Min"
					className={inputClass}
					aria-label={label + " minimum"}
				/>
				<input
					type="text"
					value={formValues[maxKey] ?? ""}
					onChange={(e) => onChange(maxKey, e.target.value)}
					placeholder="Max"
					className={inputClass}
					aria-label={label + " maximum"}
				/>
			</div>
		</div>
	);
}
