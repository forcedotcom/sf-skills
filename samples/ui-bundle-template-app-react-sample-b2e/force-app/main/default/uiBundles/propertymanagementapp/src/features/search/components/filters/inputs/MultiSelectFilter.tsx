import { ChevronDown } from "lucide-react";
import { Button } from "../../../../../components/ui/button";
import { Checkbox } from "../../../../../components/ui/checkbox";
import { Label } from "../../../../../components/ui/label";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "../../../../../components/ui/popover";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";

interface MultiSelectFilterProps {
	field: string;
	label: string;
	options: Array<{ value: string; label: string }>;
	helpText?: string;
}

export function MultiSelectFilter({ field, label, options, helpText }: MultiSelectFilterProps) {
	const { value, onChange } = useFilterField(field);
	const selected = new Set(value?.value ? value.value.split(",").filter(Boolean) : []);

	const toggle = (v: string, on: boolean) => {
		const next = new Set(selected);
		if (on) next.add(v);
		else next.delete(v);
		const joined = Array.from(next).join(",");
		if (joined === "") onChange(undefined);
		else onChange({ field, label, type: "multipicklist", value: joined });
	};

	// Summarize the selection on the collapsed trigger: the sole label when one is
	// picked, a count when several are, and a placeholder when none.
	const summary =
		selected.size === 0
			? `Select ${label.toLowerCase()}`
			: selected.size === 1
				? (options.find((o) => selected.has(o.value))?.label ?? `${selected.size} selected`)
				: `${selected.size} selected`;
	const triggerId = `filter-${field}`;

	return (
		<FilterFieldWrapper label={label} htmlFor={triggerId} helpText={helpText}>
			<Popover>
				<PopoverTrigger asChild>
					<Button
						id={triggerId}
						variant="outline"
						className="w-full justify-between font-normal"
						aria-label={`${label}: ${summary}`}
					>
						<span className={`truncate ${selected.size === 0 ? "text-foreground/70" : ""}`}>
							{summary}
						</span>
						<ChevronDown className="ml-2 size-4 shrink-0 opacity-50" aria-hidden="true" />
					</Button>
				</PopoverTrigger>
				<PopoverContent
					align="start"
					aria-label={label}
					className="w-(--radix-popover-trigger-width) max-h-72 overflow-y-auto"
				>
					<div role="group" className="flex flex-col gap-1">
						{options.length === 0 ? (
							<p className="px-1 py-2 text-sm text-muted-foreground">No options available.</p>
						) : (
							options.map((opt) => {
								const id = `filter-${field}-${opt.value}`;
								return (
									<div key={opt.value} className="flex items-center gap-2">
										<Checkbox
											id={id}
											checked={selected.has(opt.value)}
											onCheckedChange={(checked) => toggle(opt.value, checked === true)}
										/>
										<Label htmlFor={id} className="text-sm font-normal cursor-pointer">
											{opt.label}
										</Label>
									</div>
								);
							})
						)}
					</div>
				</PopoverContent>
			</Popover>
		</FilterFieldWrapper>
	);
}
