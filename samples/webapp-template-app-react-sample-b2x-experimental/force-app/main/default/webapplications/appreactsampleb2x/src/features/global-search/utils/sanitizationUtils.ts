/**
 * Sanitization Utilities
 *
 * Utility functions for sanitizing user input to prevent injection attacks.
 * These utilities provide basic sanitization for filter values.
 */

/**
 * Sanitizes a string value by removing potentially dangerous characters
 * and trimming whitespace.
 *
 * This is a basic sanitization - for production, consider using a library like DOMPurify for more
 * comprehensive sanitization.
 * Also, note this is NOT an end-to-end security control.
 * Client-side sanitization can be bypassed by any attacker using `curl` or Postman.
 * To prevent injection attacks (SOSL Injection, XSS):
 * 1. The BACKEND (Salesforce API) handles SOSL injection if parameters are passed correctly.
 * 2. React handles XSS automatically when rendering variables in JSX (e.g., <div>{value}</div>).
 * Do not rely on this function for end-to-end security enforcement.
 *
 * @param value - The string value to sanitize
 * @returns Sanitized string value
 *
 * @remarks
 * - Removes control characters (except newlines, tabs, carriage returns)
 * - Trims leading/trailing whitespace
 * - Limits length to prevent DoS attacks (default: 1000 characters)
 * - Preserves alphanumeric, spaces, and common punctuation
 *
 * @example
 * ```tsx
 * const sanitized = sanitizeFilterValue(userInput);
 * ```
 */
export function sanitizeFilterValue(value: string, maxLength: number = 1000): string {
	if (typeof value !== "string") {
		return "";
	}

	let sanitized = value.trim();

	if (sanitized.length > maxLength) {
		sanitized = sanitized.substring(0, maxLength);
	}

	sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "");

	return sanitized;
}
