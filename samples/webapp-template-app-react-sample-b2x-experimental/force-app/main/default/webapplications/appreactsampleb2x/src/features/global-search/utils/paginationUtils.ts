/**
 * Pagination Utilities
 *
 * Utility functions for pagination-related operations including page size validation.
 */

/**
 * Default page size options for pagination
 */
export const PAGE_SIZE_OPTIONS = [
	{ value: "10", label: "10" },
	{ value: "20", label: "20" },
	{ value: "50", label: "50" },
] as const;

/**
 * Valid page size values extracted from PAGE_SIZE_OPTIONS
 */
export const VALID_PAGE_SIZES = PAGE_SIZE_OPTIONS.map((opt) => parseInt(opt.value, 10));

/**
 * Validates that a page size is one of the allowed options
 * @param size - The page size to validate
 * @returns true if valid, false otherwise
 *
 * @example
 * ```tsx
 * if (isValidPageSize(userInput)) {
 *   setPageSize(userInput);
 * }
 * ```
 */
export function isValidPageSize(size: number): boolean {
	return VALID_PAGE_SIZES.includes(size);
}

/**
 * Gets a valid page size, defaulting to the first option if invalid
 * @param size - The page size to validate
 * @returns A valid page size
 *
 * @example
 * ```tsx
 * const safePageSize = getValidPageSize(userInput); // Returns valid size or default
 * ```
 */
export function getValidPageSize(size: number): number {
	return isValidPageSize(size) ? size : VALID_PAGE_SIZES[0];
}
