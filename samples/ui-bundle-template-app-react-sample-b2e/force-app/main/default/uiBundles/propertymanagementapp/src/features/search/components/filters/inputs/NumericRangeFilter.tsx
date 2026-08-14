import { useEffect, useId, useRef, useState } from "react";
import { Input } from "../../../../../components/ui/input";
import { useFilterField } from "../FilterContext";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import { debounce, FILTER_DEBOUNCE_MS } from "../../../utils/debounce";

interface NumericRangeFilterProps {
	field: string;
	label: string;
	helpText?: string;
	min?: number;
	max?: number;
}

export function NumericRangeFilter({ field, label, helpText, min, max }: NumericRangeFilterProps) {
	const { value, onChange } = useFilterField(field);
	const errorId = useId();
	const [draftMin, setDraftMin] = useState(value?.min ?? "");
	const [draftMax, setDraftMax] = useState(value?.max ?? "");

	const onChangeRef = useRef(onChange);
	useEffect(() => {
		onChangeRef.current = onChange;
	});
	// Build the debounced caller in a mount effect, not during render: creating it
	// inline would read onChangeRef.current at render time (react-hooks/refs). It
	// stays a single stable instance and always calls the latest onChange via the ref.
	const debouncedRef = useRef<((nextMin: string, nextMax: string) => void) | undefined>(undefined);
	useEffect(() => {
		debouncedRef.current = debounce((nextMin: string, nextMax: string) => {
			if (!nextMin && !nextMax) onChangeRef.current(undefined);
			else
				onChangeRef.current({
					field,
					label,
					type: "numeric",
					min: nextMin || undefined,
					max: nextMax || undefined,
				});
		}, FILTER_DEBOUNCE_MS);
	}, [field, label]);

	useEffect(() => {
		setDraftMin(value?.min ?? "");
		setDraftMax(value?.max ?? "");
	}, [value?.min, value?.max]);

	const isOutOfBounds = (v: string) => {
		if (v === "") return false;
		const n = Number(v);
		return (min != null && n < min) || (max != null && n > max);
	};
	const minOutOfBounds = isOutOfBounds(draftMin);
	const maxOutOfBounds = isOutOfBounds(draftMax);
	const isRangeInverted = draftMin !== "" && draftMax !== "" && Number(draftMin) > Number(draftMax);
	const hasError = minOutOfBounds || maxOutOfBounds || isRangeInverted;

	const boundsLabel =
		min != null && max != null
			? `${min}–${max}`
			: min != null
				? `${min} or more`
				: max != null
					? `${max} or less`
					: null;

	const errorMessage = isRangeInverted
		? "Min must not exceed max"
		: (minOutOfBounds || maxOutOfBounds) && boundsLabel
			? `Value must be between ${boundsLabel}`
			: undefined;

	return (
		<FilterFieldWrapper label={label} helpText={helpText} error={errorMessage} errorId={errorId}>
			<div className="flex items-center gap-2">
				<Input
					type="number"
					placeholder="Min"
					min={min}
					max={max}
					value={draftMin}
					onChange={(e) => {
						setDraftMin(e.target.value);
						debouncedRef.current?.(e.target.value, draftMax);
					}}
					aria-label={`${label} minimum`}
					aria-invalid={hasError || undefined}
					aria-describedby={hasError ? errorId : undefined}
				/>
				<span className="text-sm text-muted-foreground">–</span>
				<Input
					type="number"
					placeholder="Max"
					min={min}
					max={max}
					value={draftMax}
					onChange={(e) => {
						setDraftMax(e.target.value);
						debouncedRef.current?.(draftMin, e.target.value);
					}}
					aria-label={`${label} maximum`}
					aria-invalid={hasError || undefined}
					aria-describedby={hasError ? errorId : undefined}
				/>
			</div>
		</FilterFieldWrapper>
	);
}
