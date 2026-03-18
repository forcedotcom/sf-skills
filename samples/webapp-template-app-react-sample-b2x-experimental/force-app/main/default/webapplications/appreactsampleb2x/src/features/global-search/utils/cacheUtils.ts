/**
 * Cache Utilities
 *
 * Utility functions for creating deterministic cache keys and managing cache operations.
 */

import type { FilterCriteria } from "../types/filters/filters";

/**
 * Creates a deterministic cache key from filter criteria array.
 * Sorts filters and their values to ensure consistent keys regardless of input order.
 *
 * @param filters - Array of filter criteria (FilterCriteria[])
 * @returns Deterministic string key for caching
 *
 * @remarks
 * - Sorts filters by objectApiName, then fieldPath, then operator
 * - Sorts values within each filter to ensure consistency
 * - Handles null/undefined values safely
 * - Prevents cache key collisions from different object ordering
 *
 * Why is sorting required?
 * If a user filters by "Name" then "Date", the array is [Name, Date].
 * If they filter by "Date" then "Name", the array is [Date, Name].
 * - Without sorting, these would generate different cache keys ("Name-Date" vs "Date-Name"),
 * causing the app to re-fetch data it actually already has. Sorting ensures that
 * the order of user clicks doesn't invalidate the cache.
 *
 
 * @example
 * ```tsx
 * const cacheKey = createFiltersKey(filters);
 * ```
 */
export function createFiltersKey(filters: FilterCriteria[]): string {
	if (!Array.isArray(filters) || filters.length === 0) {
		return "[]";
	}

	const normalized = filters
		.map((filter) => {
			if (!filter || typeof filter !== "object") {
				return null;
			}

			const f = filter as FilterCriteria;

			const sortedValues =
				Array.isArray(f.values) && f.values.length > 0
					? [...f.values].sort((a, b) => {
							const aStr = a.toString();
							const bStr = b.toString();
							return aStr.localeCompare(bStr);
						})
					: [];

			return {
				objectApiName: f.objectApiName ?? "",
				fieldPath: f.fieldPath ?? "",
				operator: f.operator ?? "",
				values: sortedValues,
			};
		})
		.filter((f): f is NonNullable<typeof f> => f !== null)
		.sort((a, b) => {
			const objectCompare = a.objectApiName.localeCompare(b.objectApiName);
			if (objectCompare !== 0) return objectCompare;

			const fieldCompare = a.fieldPath.localeCompare(b.fieldPath);
			if (fieldCompare !== 0) return fieldCompare;

			return a.operator.localeCompare(b.operator);
		});

	return JSON.stringify(normalized);
}
