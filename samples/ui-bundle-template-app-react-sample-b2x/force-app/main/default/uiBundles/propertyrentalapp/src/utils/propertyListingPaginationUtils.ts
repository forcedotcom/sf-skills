/**
 * Page size options for property listing (token-based) pagination.
 */
export const PAGE_SIZE_OPTIONS = [
	{ value: "10", label: "10" },
	{ value: "20", label: "20" },
	{ value: "50", label: "50" },
] as const;

export const VALID_PAGE_SIZES = PAGE_SIZE_OPTIONS.map((opt) => parseInt(opt.value, 10));

export function isValidPageSize(size: number): boolean {
	return VALID_PAGE_SIZES.includes(size);
}

export function getValidPageSize(size: number): number {
	return isValidPageSize(size) ? size : VALID_PAGE_SIZES[0];
}
