import type { Filter } from "../../features/global-search/types/filters/filters";

const INPUT_CLASS =
	"h-9 px-3 rounded-md border border-gray-300 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent min-w-[140px]";

interface FilterFieldTextProps {
	filter: Filter;
	value: string;
	onChange: (value: string) => void;
}

export function FilterFieldText({ filter, value, onChange }: FilterFieldTextProps) {
	const label = filter.label || filter.targetFieldPath;
	const id = `filter-${filter.targetFieldPath}`;
	const placeholder = filter.attributes?.placeholder || `Enter ${label.toLowerCase()}`;
	return (
		<div className="flex flex-col gap-1.5 min-w-[160px]">
			<label htmlFor={id} className="text-sm font-medium text-gray-700 whitespace-nowrap">
				{label}
			</label>
			<input
				id={id}
				type="text"
				value={value}
				onChange={(e) => onChange(e.target.value)}
				placeholder={placeholder}
				className={INPUT_CLASS}
				aria-label={label}
			/>
		</div>
	);
}
