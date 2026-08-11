/**
 * Helpers for reading values out of uiapi GraphQL response nodes.
 *
 * Nodes typically come back wrapped as `{ value, displayValue }`. `fieldValue`
 * picks the user-facing string (preferring displayValue) or returns null.
 */

export function fieldValue(
	field: { displayValue?: string | null; value?: unknown } | null | undefined,
): string | null {
	if (field?.displayValue != null) return field.displayValue;
	if (field?.value != null) return String(field.value);
	return null;
}
