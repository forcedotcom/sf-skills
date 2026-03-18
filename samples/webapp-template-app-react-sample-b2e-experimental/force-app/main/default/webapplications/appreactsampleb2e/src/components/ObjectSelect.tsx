const selectClass =
	"h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-purple/20 focus:border-primary-purple min-w-[180px]";

export interface ObjectSelectOption {
	value: string;
	label: string;
}

interface ObjectSelectProps {
	options: ObjectSelectOption[];
	value: string;
	onChange: (value: string) => void;
	"aria-label"?: string;
}

/**
 * Shadcn-style select for object type (Properties, Maintenance Requests, Maintenance Workers).
 */
export function ObjectSelect({
	options,
	value,
	onChange,
	"aria-label": ariaLabel = "Search in",
}: ObjectSelectProps) {
	return (
		<select
			className={selectClass}
			value={value}
			onChange={(e) => onChange(e.target.value)}
			aria-label={ariaLabel}
		>
			{options.map((opt) => (
				<option key={opt.value} value={opt.value}>
					{opt.label}
				</option>
			))}
		</select>
	);
}
