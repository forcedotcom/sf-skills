import type { FieldValue, ComplexFieldValue } from "../types/search/searchResults";

const DISPLAY_FIELD_CANDIDATES = [
	"Name",
	"CaseNumber",
	"Subject",
	"Title",
	"DeveloperName",
	"ContractNumber",
];
/**
 * Extracts the display value from a field value, handling nested structures
 * For complex fields like Owner, extracts nested values from fields.Name.value
 */
export function extractFieldValue(
	fieldValue: FieldValue | undefined,
	useDisplayValue: boolean = false,
): string {
	if (!fieldValue) {
		return "—";
	}

	// If displayValue exists and is not null, use it (highest priority)
	if (useDisplayValue && isDefined(fieldValue.displayValue)) {
		return fieldValue.displayValue;
	}

	// If value is a complex object (like Owner), extract nested value
	if (isComplexValue(fieldValue.value)) {
		return extractComplexValue(fieldValue.value as ComplexFieldValue) ?? "—";
	}

	// Otherwise use the value directly (for simple fields)
	if (isDefined(fieldValue.value)) {
		return fieldValue.value as string;
	}

	return "—";
}

/**
 * Helper to safely extract name from related object
 */
function extractComplexValue(complex: ComplexFieldValue): string | null {
	const fields = complex.fields;
	if (!fields) return null;
	// Scale: Check the candidate list until we find a field that exists and has a value
	for (const fieldName of DISPLAY_FIELD_CANDIDATES) {
		const field = fields[fieldName];
		if (field) {
			// Priority: DisplayValue -> Value
			if (isDefined(field.displayValue)) return field.displayValue;
			if (isDefined(field.value)) return field.value as string;
		}
	}

	return null;
}
/**
 * Type Guard checks
 */
function isDefined(val: unknown): val is string | number | boolean {
	return val !== null && val !== undefined;
}
function isComplexValue(val: unknown): val is ComplexFieldValue {
	return typeof val === "object" && val !== null;
}
