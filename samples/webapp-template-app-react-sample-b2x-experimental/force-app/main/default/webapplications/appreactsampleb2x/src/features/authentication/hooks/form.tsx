import { useId } from "react";
import { createFormHookContexts, createFormHook } from "@tanstack/react-form";
import {
	Field,
	FieldDescription,
	FieldError,
	FieldLabel,
} from "../../../components/ui/field";
import { Input } from "../../../components/ui/input";
import { cn } from "../../../lib/utils";
import { AUTH_PLACEHOLDERS } from "../authenticationConfig";

// Create form hook contexts
export const { fieldContext, formContext, useFieldContext, useFormContext } =
	createFormHookContexts();

// ============================================================================
// Field Components
// ============================================================================

interface TextFieldProps extends Omit<
	React.ComponentProps<typeof Input>,
	"name" | "value" | "onBlur" | "onChange" | "aria-invalid"
> {
	label: string;
	labelAction?: React.ReactNode;
	description?: React.ReactNode;
}

function TextField({
	label,
	id: providedId,
	labelAction,
	description,
	type = "text",
	...props
}: TextFieldProps) {
	const field = useFieldContext<string>();
	const generatedId = useId();
	const id = providedId ?? generatedId;
	const descriptionId = `${id}-description`;
	const errorId = `${id}-error`;
	const isInvalid = field.state.meta.isTouched && field.state.meta.errors.length > 0;

	// Deduplicate errors by message
	const errors = field.state.meta.errors;
	const uniqueErrors = [...new Map(errors.map((item: any) => [item["message"], item])).values()];

	return (
		<Field data-invalid={isInvalid}>
			<div className="flex items-center">
				<FieldLabel htmlFor={id}>{label}</FieldLabel>
				{labelAction && <div className="ml-auto">{labelAction}</div>}
			</div>
			{description && <FieldDescription id={descriptionId}>{description}</FieldDescription>}
			<Input
				id={id}
				name={field.name as string}
				type={type}
				value={field.state.value ?? ""}
				onBlur={field.handleBlur}
				onChange={(e: React.ChangeEvent<HTMLInputElement>) => field.handleChange(e.target.value)}
				aria-invalid={isInvalid}
				aria-describedby={cn(description && descriptionId, isInvalid && errorId)}
				{...props}
			/>
			{isInvalid && uniqueErrors.length > 0 && <FieldError errors={uniqueErrors} />}
		</Field>
	);
}

/** Password field with preset type and autocomplete */
function PasswordField({
	label,
	autoComplete = "current-password",
	placeholder = AUTH_PLACEHOLDERS.PASSWORD,
	...props
}: Omit<TextFieldProps, "type">) {
	return (
		<TextField
			label={label}
			type="password"
			autoComplete={autoComplete}
			placeholder={placeholder}
			{...props}
		/>
	);
}

/** Email field with preset type and autocomplete */
function EmailField({
	label,
	placeholder = AUTH_PLACEHOLDERS.EMAIL,
	...props
}: Omit<TextFieldProps, "type">) {
	return (
		<TextField
			label={label}
			type="email"
			autoComplete="username"
			placeholder={placeholder}
			{...props}
		/>
	);
}

// ============================================================================
// Create Form Hook
// ============================================================================

export const { useAppForm } = createFormHook({
	fieldContext,
	formContext,
	fieldComponents: {
		TextField,
		PasswordField,
		EmailField,
	},
	formComponents: {},
});
