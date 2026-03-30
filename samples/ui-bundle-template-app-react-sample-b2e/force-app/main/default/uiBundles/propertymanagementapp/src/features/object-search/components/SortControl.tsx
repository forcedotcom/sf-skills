import { ArrowUp, ArrowDown } from "lucide-react";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../components/ui/select";
import { Button } from "../../../components/ui/button";
import { cn } from "../../../lib/utils";
import type { SortFieldConfig, SortState } from "../utils/sortUtils";

const NONE_VALUE = "__none__";

interface SortControlProps extends React.ComponentProps<"div"> {
	configs: SortFieldConfig[];
	sort: SortState | null;
	onSortChange: (sort: SortState | null) => void;
	labelProps?: React.ComponentProps<"span">;
	selectProps?: Omit<
		React.ComponentProps<typeof SortControlSelect>,
		"configs" | "sort" | "onSortChange"
	>;
	directionButtonProps?: Omit<
		React.ComponentProps<typeof SortDirectionButton>,
		"sort" | "onSortChange"
	>;
}

export function SortControl({
	configs,
	sort,
	onSortChange,
	className,
	labelProps,
	selectProps,
	directionButtonProps,
	...props
}: SortControlProps) {
	return (
		<div className={cn("flex items-center gap-2", className)} {...props}>
			<span
				{...labelProps}
				className={cn("text-sm text-muted-foreground whitespace-nowrap", labelProps?.className)}
			>
				{labelProps?.children ?? "Sort by"}
			</span>
			<SortControlSelect
				configs={configs}
				sort={sort}
				onSortChange={onSortChange}
				{...selectProps}
			/>
			{sort && (
				<SortDirectionButton sort={sort} onSortChange={onSortChange} {...directionButtonProps} />
			)}
		</div>
	);
}

interface SortControlSelectProps {
	configs: SortFieldConfig[];
	sort: SortState | null;
	onSortChange: (sort: SortState | null) => void;
	triggerProps?: React.ComponentProps<typeof SelectTrigger>;
	contentProps?: React.ComponentProps<typeof SelectContent>;
	selectValueProps?: React.ComponentProps<typeof SelectValue>;
	selectItemProps?: Omit<React.ComponentProps<typeof SelectItem>, "value">;
}

export function SortControlSelect({
	configs,
	sort,
	onSortChange,
	triggerProps,
	contentProps,
	selectValueProps,
	selectItemProps,
}: SortControlSelectProps) {
	return (
		<Select
			value={sort?.field ?? NONE_VALUE}
			onValueChange={(v) => {
				if (v === NONE_VALUE) {
					onSortChange(null);
				} else {
					onSortChange({
						field: v,
						direction: sort?.direction ?? "ASC",
					});
				}
			}}
		>
			<SelectTrigger
				size="sm"
				{...triggerProps}
				className={cn("w-[160px]", triggerProps?.className)}
			>
				<SelectValue placeholder="Default" {...selectValueProps} />
			</SelectTrigger>
			<SelectContent {...contentProps}>
				<SelectItem value={NONE_VALUE} {...selectItemProps}>
					Default
				</SelectItem>
				{configs.map((c) => (
					<SelectItem key={c.field} value={c.field} {...selectItemProps}>
						{c.label}
					</SelectItem>
				))}
			</SelectContent>
		</Select>
	);
}

interface SortDirectionButtonProps extends React.ComponentProps<typeof Button> {
	sort: SortState;
	onSortChange: (sort: SortState) => void;
}

export function SortDirectionButton({
	sort,
	onSortChange,
	className,
	...props
}: SortDirectionButtonProps) {
	return (
		<Button
			variant="ghost"
			size="icon-sm"
			className={cn(className)}
			onClick={() =>
				onSortChange({
					...sort,
					direction: sort.direction === "ASC" ? "DESC" : "ASC",
				})
			}
			aria-label={`Sort ${sort.direction === "ASC" ? "descending" : "ascending"}`}
			{...props}
		>
			{sort.direction === "ASC" ? <ArrowUp /> : <ArrowDown />}
		</Button>
	);
}
