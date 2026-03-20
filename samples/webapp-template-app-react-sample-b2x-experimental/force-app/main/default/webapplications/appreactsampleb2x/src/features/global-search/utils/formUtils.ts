/**
 * Form Utilities
 *
 * Utility functions for form validation and error handling.
 * These utilities are framework-agnostic and can be used with any form library.
 */

/**
 * Form error structure from TanStack Form
 * Errors can be objects with a message property or strings
 */
export interface FormError {
	message: string;
	[key: string]: unknown;
}

/**
 * Type guard to check if an error has a message property
 * @param error - The error to check
 * @returns true if the error has a message property
 */
export function isFormError(error: unknown): error is FormError {
	return (
		typeof error === "object" &&
		error !== null &&
		"message" in error &&
		typeof (error as FormError).message === "string"
	);
}

/**
 * Extracts unique errors by message, filtering out duplicates
 * Handles both Error objects and string errors
 * Converts FormError objects to Error instances for compatibility with UI components
 *
 * @param errors - Array of error objects or strings from form libraries
 * @returns Array of unique Error objects (compatible with FieldError component)
 *
 * @example
 * ```tsx
 * const uniqueErrors = getUniqueErrors(formErrors);
 * ```
 */
export function getUniqueErrors(errors: unknown[]): Error[] {
	const errorMap = new Map<string, Error>();

	for (const error of errors) {
		if (isFormError(error)) {
			// Use message as key to deduplicate
			if (!errorMap.has(error.message)) {
				// Convert FormError to Error for compatibility
				const errorObj = new Error(error.message);
				// Preserve additional properties if needed
				Object.assign(errorObj, error);
				errorMap.set(error.message, errorObj);
			}
		} else if (typeof error === "string") {
			// Handle string errors
			if (!errorMap.has(error)) {
				errorMap.set(error, new Error(error));
			}
		} else if (error instanceof Error) {
			// Handle Error objects directly
			if (!errorMap.has(error.message)) {
				errorMap.set(error.message, error);
			}
		}
	}

	return Array.from(errorMap.values());
}

/**
 * Validates that min value is less than or equal to max value for range filters
 * This utility can be used in form validation logic
 *
 * @param minValue - Minimum value (string or number)
 * @param maxValue - Maximum value (string or number)
 * @returns Error message if validation fails, null if valid
 *
 * @remarks
 * - If both values are empty, validation passes
 * - Only validates if both values can be parsed as numbers
 * - Returns null if values cannot be parsed (lets other validators handle it)
 *
 * @example
 * ```tsx
 * // In form validation
 * const minError = validateRangeValues(minFieldValue, maxFieldValue);
 * if (minError) {
 *   setFieldError('minField', minError);
 * }
 * ```
 */
export function validateRangeValues(
	minValue: string | number | null | undefined,
	maxValue: string | number | null | undefined,
): string | null {
	// If both are empty, validation passes
	if (!minValue && !maxValue) {
		return null;
	}

	// Parse values to numbers if possible
	const parseValue = (val: string | number | null | undefined): number | null => {
		if (!val) {
			return null;
		}
		if (typeof val === "number") {
			return val;
		}
		const parsed = parseInt(val, 10);
		return isNaN(parsed) ? null : parsed;
	};

	const minNum = parseValue(minValue);
	const maxNum = parseValue(maxValue);

	// If one is not a number, skip numeric validation (let other validators handle it)
	if (minNum === null || maxNum === null) {
		return null;
	}

	// Validate min <= max
	if (minNum > maxNum) {
		return "Minimum value must be less than or equal to maximum value";
	}

	return null;
}

export function getFormValueByPath(record: Record<string, unknown>, fieldPath: string): string {
	if (!fieldPath) return "";
	const parts = fieldPath.split(".");
	let current: Record<string, unknown> = record;
	for (const part of parts) {
		if (current == null || typeof current !== "object") return "";
		current = (current as Record<string, unknown>)[part] as unknown as Record<string, unknown>;
	}
	if (current === undefined || current === null) return "";
	return "" + current;
}
