/**
 * Filter Utilities
 *
 * Utility functions for filter value parsing and transformation.
 * These utilities handle the conversion of form values to filter criteria.
 */

/**
 * Parses a string value to either a number or string
 * Attempts to parse as integer, falls back to trimmed string if not a valid number
 *
 * @param val - The value to parse (string)
 * @returns Parsed number if valid, otherwise trimmed string, or empty string if input is empty
 *
 * @remarks
 * - Returns empty string for empty/whitespace input
 * - Attempts integer parsing first
 * - Falls back to trimmed string if parsing fails
 * - Used for filter values that can be either numeric or text
 *
 * @example
 * ```tsx
 * const parsed = parseFilterValue("123"); // 123 (number)
 * const parsed = parseFilterValue("abc"); // "abc" (string)
 * const parsed = parseFilterValue("  "); // "" (empty string)
 * ```
 */
export function parseFilterValue(val: string): string | number {
	if (!val.trim()) return "";
	const numVal = parseInt(val.trim(), 10);
	return isNaN(numVal) ? val.trim() : numVal;
}
