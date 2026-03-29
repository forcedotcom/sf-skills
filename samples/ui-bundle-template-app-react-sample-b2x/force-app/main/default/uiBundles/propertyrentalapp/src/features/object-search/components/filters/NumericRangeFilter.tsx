import { useEffect, useState } from "react";
import { Input } from "../../../../components/ui/input";

import { useFilterField } from "../FilterContext";
import { useDebouncedCallback } from "../../hooks/useDebouncedCallback";
import { FilterFieldWrapper } from "./FilterFieldWrapper";
import type { ActiveFilterValue } from "../../utils/filterUtils";

interface NumericRangeFilterProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	helpText?: string;
	min?: number;
	max?: number;
}

export function NumericRangeFilter({
	field,
	label,
	helpText,
	min,
	max,
	className,
	...props
}: NumericRangeFilterProps) {
	const { value, onChange } = useFilterField(field);
	return (
		<NumericRangeFilterInputs
			field={field}
			label={label}
			helpText={helpText}
			value={value}
			onChange={onChange}
			min={min}
			max={max}
			className={className}
			{...props}
		/>
	);
}

interface NumericRangeFilterInputsProps extends Omit<React.ComponentProps<"div">, "onChange"> {
	field: string;
	label: string;
	helpText?: string;
	value: ActiveFilterValue | undefined;
	onChange: (value: ActiveFilterValue | undefined) => void;
	min?: number;
	max?: number;
	minInputProps?: React.ComponentProps<typeof Input>;
	maxInputProps?: React.ComponentProps<typeof Input>;
}

export function NumericRangeFilterInputs({
	field,
	label,
	helpText,
	value,
	onChange,
	min: boundMin,
	max: boundMax,
	className,
	...props
}: NumericRangeFilterInputsProps) {
	const [localMin, setLocalMin] = useState(value?.min ?? "");
	const [localMax, setLocalMax] = useState(value?.max ?? "");

	const externalMin = value?.min ?? "";
	const externalMax = value?.max ?? "";
	useEffect(() => {
		setLocalMin(externalMin);
	}, [externalMin]);
	useEffect(() => {
		setLocalMax(externalMax);
	}, [externalMax]);

	const isOutOfBounds = (v: string) => {
		if (v === "") return false;
		const n = Number(v);
		return (boundMin != null && n < boundMin) || (boundMax != null && n > boundMax);
	};
	const minOutOfBounds = isOutOfBounds(localMin);
	const maxOutOfBounds = isOutOfBounds(localMax);
	const isRangeInverted = localMin !== "" && localMax !== "" && Number(localMin) > Number(localMax);
	const hasError = minOutOfBounds || maxOutOfBounds || isRangeInverted;

	const debouncedOnChange = useDebouncedCallback((min: string, max: string) => {
		if (!min && !max) {
			onChange(undefined);
			return;
		}
		const minNum = min !== "" ? Number(min) : null;
		const maxNum = max !== "" ? Number(max) : null;
		if (minNum != null && maxNum != null && minNum > maxNum) return;
		if (
			minNum != null &&
			((boundMin != null && minNum < boundMin) || (boundMax != null && minNum > boundMax))
		)
			return;
		if (
			maxNum != null &&
			((boundMin != null && maxNum < boundMin) || (boundMax != null && maxNum > boundMax))
		)
			return;
		onChange({ field, label, type: "numeric" as const, min, max });
	});

	const boundsLabel =
		boundMin != null && boundMax != null
			? `${boundMin}–${boundMax}`
			: boundMin != null
				? `${boundMin} or more`
				: boundMax != null
					? `${boundMax} or less`
					: null;

	const errorMessage = isRangeInverted
		? "Min must not exceed max"
		: (minOutOfBounds || maxOutOfBounds) && boundsLabel
			? `Value must be between ${boundsLabel}`
			: undefined;

	return (
		<FilterFieldWrapper
			label={label}
			helpText={helpText}
			error={errorMessage}
			className={className}
			{...props}
		>
			<div className="flex gap-2">
				<Input
					type="number"
					placeholder="Min"
					value={localMin}
					min={boundMin}
					max={boundMax}
					onChange={(e) => {
						const v = e.target.value;
						setLocalMin(v);
						debouncedOnChange(v, localMax);
					}}
					aria-label={`${label} minimum`}
					aria-invalid={hasError || undefined}
				/>
				<Input
					type="number"
					placeholder="Max"
					value={localMax}
					min={boundMin}
					max={boundMax}
					onChange={(e) => {
						const v = e.target.value;
						setLocalMax(v);
						debouncedOnChange(localMin, v);
					}}
					aria-label={`${label} maximum`}
					aria-invalid={hasError || undefined}
				/>
			</div>
		</FilterFieldWrapper>
	);
}
