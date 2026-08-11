import { ArrowDown, ArrowUp } from "lucide-react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../components/ui/select";
import { Button } from "../../../../components/ui/button";
import type { SortFieldConfig, SortState } from "../../utils/sortUtils";

const NONE_VALUE = "__none__";

interface SortControlProps {
	configs: SortFieldConfig[];
	sort: SortState | null;
	onSortChange: (sort: SortState | null) => void;
	className?: string;
}

export function SortControl({ configs, sort, onSortChange, className }: SortControlProps) {
	if (configs.length === 0) return null;
	return (
		<div className={`flex items-center gap-2 ${className ?? ""}`}>
			<span className="text-sm text-muted-foreground whitespace-nowrap">Sort by</span>
			<Select
				value={sort?.field ?? NONE_VALUE}
				onValueChange={(v) => {
					if (v === NONE_VALUE) onSortChange(null);
					else onSortChange({ field: v, direction: sort?.direction ?? "ASC" });
				}}
			>
				<SelectTrigger size="sm" className="w-[160px]" aria-label="Sort by">
					<SelectValue placeholder="Default" />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value={NONE_VALUE}>Default</SelectItem>
					{configs.map((c) => (
						<SelectItem key={c.field} value={c.field}>
							{c.label}
						</SelectItem>
					))}
				</SelectContent>
			</Select>
			{sort && (
				<Button
					variant="ghost"
					size="icon-sm"
					onClick={() =>
						onSortChange({
							...sort,
							direction: sort.direction === "ASC" ? "DESC" : "ASC",
						})
					}
					aria-label={`Sort ${sort.direction === "ASC" ? "descending" : "ascending"}`}
				>
					{sort.direction === "ASC" ? <ArrowUp /> : <ArrowDown />}
				</Button>
			)}
		</div>
	);
}
