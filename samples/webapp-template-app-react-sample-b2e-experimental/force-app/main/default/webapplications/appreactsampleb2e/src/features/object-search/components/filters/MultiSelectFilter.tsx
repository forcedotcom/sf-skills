import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "../../../../components/ui/popover";
import { Checkbox } from "../../../../components/ui/checkbox";
import { Label } from "../../../../components/ui/label";
import { Button } from "../../../../components/ui/button";
import { cn } from "../../../../lib/utils";
import { ChevronDown } from "lucide-react";
import type { FilterFieldConfig, ActiveFilterValue } from "../../utils/filterUtils";

interface MultiSelectFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	config: FilterFieldConfig;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	labelProps?: React.ComponentProps<typeof Label>;
	helpTextProps?: React.ComponentProps<"p">;
}

export function MultiSelectFilter({
	config,
	value,
	onChange,
	className,
	labelProps,
	helpTextProps,
	...props
}: MultiSelectFilterProps) {
	const selected = value?.value ? value.value.split(",") : [];

	const triggerLabel =
		selected.length === 0
			? `Select ${config.label.toLowerCase()}`
			: selected.length === 1
				? (config.options?.find((o) => o.value === selected[0])?.label ?? selected[0])
				: `${selected.length} selected`;

	function handleToggle(optionValue: string) {
		const next = selected.includes(optionValue)
			? selected.filter((v) => v !== optionValue)
			: [...selected, optionValue];

		if (next.length === 0) {
			onChange(undefined);
		} else {
			onChange({
				field: config.field,
				label: config.label,
				type: "multipicklist",
				value: next.join(","),
			});
		}
	}

	return (
		<div className={cn("space-y-1.5", className)} {...props}>
			<Label {...labelProps}>{labelProps?.children ?? config.label}</Label>
			<Popover>
				<PopoverTrigger asChild>
					<Button
						variant="outline"
						role="combobox"
						className={cn(
							"w-full justify-between font-normal",
							selected.length === 0 && "text-muted-foreground",
						)}
					>
						<span className="truncate">{triggerLabel}</span>
						<ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
					</Button>
				</PopoverTrigger>
				<PopoverContent className="p-2" align="start">
					<div className="max-h-48 overflow-y-auto space-y-1">
						{config.options?.map((opt) => {
							const id = `filter-${config.field}-${opt.value}`;
							return (
								<div
									key={opt.value}
									className="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-accent"
								>
									<Checkbox
										id={id}
										checked={selected.includes(opt.value)}
										onCheckedChange={() => handleToggle(opt.value)}
									/>
									<Label htmlFor={id} className="text-sm font-normal cursor-pointer w-full">
										{opt.label}
									</Label>
								</div>
							);
						})}
					</div>
				</PopoverContent>
			</Popover>
			{config.helpText && (
				<p
					{...helpTextProps}
					className={cn("text-xs text-muted-foreground", helpTextProps?.className)}
				>
					{helpTextProps?.children ?? config.helpText}
				</p>
			)}
		</div>
	);
}
