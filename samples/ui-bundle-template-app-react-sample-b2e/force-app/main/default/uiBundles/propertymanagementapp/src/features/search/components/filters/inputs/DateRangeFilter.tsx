import { useState } from "react";
import { Input } from "../../../../../components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../../../components/ui/select";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import type {
	ActiveFilterValue,
	DateFilterMode,
	FilterFieldType,
} from "../../../utils/filterUtils";

interface DateRangeFilterProps {
	field: string;
	label: string;
	helpText?: string;
	/** "daterange" (Date scalar) or "datetimerange" (DateTime scalar). */
	filterType?: Extract<FilterFieldType, "daterange" | "datetimerange">;
	/**
	 * Which comparison chrome to show. See {@link DateFilterMode}. Defaults to
	 * `"comparison"` (an After / Before selector with one date input).
	 */
	mode?: DateFilterMode;
}

/**
 * The three ways to constrain a date field. They map directly onto the
 * `min`/`max` bounds the query builder already understands:
 *   - after   → only `min` set  → `gte`
 *   - before  → only `max` set  → `lte`
 *   - between → both set        → `gte` AND `lte`
 */
type DateOperator = "between" | "after" | "before";

const OPERATOR_LABELS: Record<DateOperator, string> = {
	between: "Between",
	after: "After",
	before: "Before",
};

/** The operators offered for each {@link DateFilterMode}. */
const MODE_OPERATORS: Record<DateFilterMode, DateOperator[]> = {
	range: ["between"],
	comparison: ["after", "before"],
	both: ["between", "after", "before"],
};

/** Pick the operator implied by an already-active filter (e.g. restored from the URL). */
function operatorFor(value: ActiveFilterValue | undefined): DateOperator {
	const hasMin = !!value?.min;
	const hasMax = !!value?.max;
	if (hasMax && !hasMin) return "before";
	if (hasMin && !hasMax) return "after";
	return "between";
}

/**
 * A date constraint whose chrome is driven by `mode`:
 *   - `"range"`: a single Between control (two date inputs).
 *   - `"comparison"` (default): an After / Before selector with one input.
 *   - `"both"`: a Between / After / Before selector spanning the two.
 *
 * "Between" shows two `<input type="date">` controls; "After" / "Before"
 * collapse to one bound to the relevant end. Uses the platform-native picker —
 * no popover/calendar dependency.
 */
export function DateRangeFilter({
	field,
	label,
	helpText,
	filterType = "daterange",
	mode = "comparison",
}: DateRangeFilterProps) {
	const { value, onChange } = useFilterField(field);
	const operators = MODE_OPERATORS[mode];

	// Operator is local UI state: it must survive a moment where no date is yet
	// entered (which clears the active filter), so it can't be derived from
	// `value` on every render. Seed it from any filter restored on mount, clamped
	// to an operator this mode actually offers.
	const [operator, setOperator] = useState<DateOperator>(() => {
		const restored = operatorFor(value);
		return operators.includes(restored) ? restored : operators[0];
	});

	const emit = (nextMin: string | undefined, nextMax: string | undefined) => {
		if (!nextMin && !nextMax) onChange(undefined);
		else onChange({ field, label, type: filterType, min: nextMin, max: nextMax });
	};

	const changeOperator = (next: DateOperator) => {
		setOperator(next);
		// Re-emit, keeping only the bound(s) the new operator uses.
		if (next === "after") emit(value?.min, undefined);
		else if (next === "before") emit(undefined, value?.max);
		else emit(value?.min, value?.max);
	};

	const operatorId = `filter-${field}-op`;
	// A lone "between" operator (mode="range") needs no selector — it can't change.
	const showSelector = operators.length > 1;

	return (
		<FilterFieldWrapper label={label} helpText={helpText}>
			<div className="flex flex-col gap-2">
				{showSelector && (
					<Select value={operator} onValueChange={(v) => changeOperator(v as DateOperator)}>
						<SelectTrigger id={operatorId} className="w-full" aria-label={`${label} comparison`}>
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							{operators.map((op) => (
								<SelectItem key={op} value={op}>
									{OPERATOR_LABELS[op]}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
				)}

				{operator === "between" ? (
					<div className="flex items-center gap-2">
						<Input
							type="date"
							value={value?.min ?? ""}
							onChange={(e) => emit(e.target.value || undefined, value?.max)}
							aria-label={`${label} from`}
						/>
						<span className="text-sm text-muted-foreground">–</span>
						<Input
							type="date"
							value={value?.max ?? ""}
							onChange={(e) => emit(value?.min, e.target.value || undefined)}
							aria-label={`${label} to`}
						/>
					</div>
				) : operator === "after" ? (
					<Input
						type="date"
						value={value?.min ?? ""}
						onChange={(e) => emit(e.target.value || undefined, undefined)}
						aria-label={`${label} after`}
					/>
				) : (
					<Input
						type="date"
						value={value?.max ?? ""}
						onChange={(e) => emit(undefined, e.target.value || undefined)}
						aria-label={`${label} before`}
					/>
				)}
			</div>
		</FilterFieldWrapper>
	);
}
