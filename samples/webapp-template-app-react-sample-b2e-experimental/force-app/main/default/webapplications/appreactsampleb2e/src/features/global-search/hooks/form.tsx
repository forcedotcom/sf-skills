import { useId } from "react";
import { createFormHookContexts, createFormHook } from "@tanstack/react-form";
import {
	Field,
	FieldDescription,
	FieldError,
	FieldLabel,
} from "../../../components/ui/field";
import { Input } from "../../../components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../../../components/ui/select";
import { cn } from "../../../lib/utils";
import type { PicklistValue } from "../types/filters/picklist";
import { getUniqueErrors } from "../utils/formUtils";

export type { FormError } from "../utils/formUtils";
export { validateRangeValues } from "../utils/formUtils";

export const { fieldContext, formContext, useFieldContext, useFormContext } =
	createFormHookContexts();

interface FilterTextFieldProps extends Omit<
	React.ComponentProps<typeof Input>,
	"name" | "value" | "onBlur" | "onChange" | "aria-invalid"
> {
	label: string;
	description?: React.ReactNode;
	placeholder?: string;
}

function FilterTextField({
	label,
	id: providedId,
	description,
	placeholder,
	type = "text",
	...props
}: FilterTextFieldProps) {
	const field = useFieldContext<string>();
	const generatedId = useId();
	const id = providedId ?? generatedId;
	const descriptionId = `${id}-description`;
	const errorId = `${id}-error`;
	const isInvalid = field.state.meta.isTouched && field.state.meta.errors.length > 0;

	const uniqueErrors = getUniqueErrors(field.state.meta.errors);

	return (
		<Field data-invalid={isInvalid}>
			<FieldLabel htmlFor={id}>{label}</FieldLabel>
			{description && <FieldDescription id={descriptionId}>{description}</FieldDescription>}
			<Input
				id={id}
				name={field.name as string}
				type={type}
				value={field.state.value ?? ""}
				onBlur={field.handleBlur}
				onChange={(e: React.ChangeEvent<HTMLInputElement>) => field.handleChange(e.target.value)}
				placeholder={placeholder}
				aria-invalid={isInvalid}
				aria-describedby={cn(description && descriptionId, isInvalid && errorId)}
				{...props}
			/>
			{isInvalid && uniqueErrors.length > 0 && <FieldError errors={uniqueErrors} />}
		</Field>
	);
}

interface FilterSelectFieldProps {
	label: string;
	id?: string;
	description?: React.ReactNode;
	placeholder?: string;
	options: PicklistValue[];
}

function FilterSelectField({
	label,
	id: providedId,
	description,
	placeholder = "Select...",
	options,
}: FilterSelectFieldProps) {
	const field = useFieldContext<string>();
	const generatedId = useId();
	const id = providedId ?? generatedId;
	const descriptionId = `${id}-description`;
	const errorId = `${id}-error`;
	const isInvalid = field.state.meta.isTouched && field.state.meta.errors.length > 0;

	const uniqueErrors = getUniqueErrors(field.state.meta.errors);

	return (
		<Field data-invalid={isInvalid}>
			<FieldLabel htmlFor={id}>{label}</FieldLabel>
			{description && <FieldDescription id={descriptionId}>{description}</FieldDescription>}
			<Select value={field.state.value ?? ""} onValueChange={(value) => field.handleChange(value)}>
				<SelectTrigger
					id={id}
					aria-invalid={isInvalid}
					aria-describedby={cn(description && descriptionId, isInvalid && errorId)}
				>
					<SelectValue placeholder={placeholder} />
				</SelectTrigger>
				<SelectContent>
					{options.map((option) => {
						if (!option || !option.value) return null;
						return (
							<SelectItem key={option.value} value={option.value}>
								{option.label || option.value}
							</SelectItem>
						);
					})}
				</SelectContent>
			</Select>
			{isInvalid && uniqueErrors.length > 0 && <FieldError errors={uniqueErrors} />}
		</Field>
	);
}

interface FilterRangeFieldProps extends Omit<
	React.ComponentProps<typeof Input>,
	"name" | "value" | "onBlur" | "onChange" | "aria-invalid"
> {
	label?: string;
	description?: React.ReactNode;
	placeholder?: string;
}

function FilterRangeFieldBase({
	label,
	id: providedId,
	description,
	placeholder,
	type = "text",
	...props
}: FilterRangeFieldProps) {
	const field = useFieldContext<string>();
	const generatedId = useId();
	const id = providedId ?? generatedId;
	const descriptionId = `${id}-description`;
	const errorId = `${id}-error`;
	const isInvalid = field.state.meta.isTouched && field.state.meta.errors.length > 0;

	const uniqueErrors = getUniqueErrors(field.state.meta.errors);

	return (
		<div>
			{label && <FieldLabel htmlFor={id}>{label}</FieldLabel>}
			{description && <FieldDescription id={descriptionId}>{description}</FieldDescription>}
			<Input
				id={id}
				name={field.name as string}
				type={type}
				value={field.state.value ?? ""}
				onBlur={field.handleBlur}
				onChange={(e: React.ChangeEvent<HTMLInputElement>) => field.handleChange(e.target.value)}
				placeholder={placeholder}
				aria-invalid={isInvalid}
				aria-describedby={cn(description && descriptionId, isInvalid && errorId)}
				{...props}
			/>
			{isInvalid && uniqueErrors.length > 0 && <FieldError errors={uniqueErrors} />}
		</div>
	);
}

interface FilterRangeMinFieldProps extends Omit<
	React.ComponentProps<typeof Input>,
	"name" | "value" | "onBlur" | "onChange" | "aria-invalid"
> {
	label?: string;
	description?: React.ReactNode;
	placeholder?: string;
}

interface FilterRangeMaxFieldProps extends Omit<
	React.ComponentProps<typeof Input>,
	"name" | "value" | "onBlur" | "onChange" | "aria-invalid"
> {
	label?: string;
	description?: React.ReactNode;
	placeholder?: string;
}

function FilterRangeMinField({ placeholder = "Min", ...props }: FilterRangeMinFieldProps) {
	return <FilterRangeFieldBase placeholder={placeholder} {...props} />;
}

function FilterRangeMaxField({ placeholder = "Max", ...props }: FilterRangeMaxFieldProps) {
	return <FilterRangeFieldBase placeholder={placeholder} {...props} />;
}

export const { useAppForm } = createFormHook({
	fieldContext,
	formContext,
	fieldComponents: {
		FilterTextField,
		FilterSelectField,
		FilterRangeMinField,
		FilterRangeMaxField,
	},
	formComponents: {},
});
