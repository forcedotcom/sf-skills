import { Label } from "../../../../components/ui/label";
import { cn } from "../../../../lib/utils";
import { SearchBar } from "../SearchBar";
import type { FilterFieldConfig, ActiveFilterValue } from "../../utils/filterUtils";

interface SearchFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	labelProps?: React.ComponentProps<typeof Label>;
}

export function SearchFilter({
	config,
	value,
	onChange,
	className,
	labelProps,
	...props
}: SearchFilterProps) {
	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label htmlFor={`filter-${config.field}`} {...labelProps}>
				{labelProps?.children ?? config.label}
			</Label>
			<SearchBar
				value={value?.value ?? ""}
				handleChange={(v) => {
					if (v) {
						onChange({ field: config.field, label: config.label, type: "search", value: v });
					} else {
						onChange(undefined);
					}
				}}
				placeholder={config.placeholder}
				inputProps={{ id: `filter-${config.field}` }}
			/>
		</div>
	);
}
