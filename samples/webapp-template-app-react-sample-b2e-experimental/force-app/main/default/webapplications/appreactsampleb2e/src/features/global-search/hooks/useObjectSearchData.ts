/**
 * Object Search Data Hooks
 *
 * - useObjectListMetadata: single source for list-view metadata (filters → columns + picklists). Use in list pages to avoid duplicate state and API calls.
 * - useObjectColumns / useObjectFilters: thin wrappers over useObjectListMetadata for backward compatibility.
 * - getSharedFilters: module-level deduplication for getObjectListFilters across hook instances.
 */

import { useState, useEffect } from "react";
import { objectInfoService } from "../api/objectInfoService";
import type { Column } from "../types/search/searchResults";
import type { Filter } from "../types/filters/filters";
import type { PicklistValue } from "../types/filters/picklist";

// --- Shared filters cache (deduplicates getObjectListFilters across useObjectColumns + useObjectFilters) ---
const sharedFiltersCache = new Map<string, Filter[]>();
const sharedFiltersInFlight = new Map<string, Promise<Filter[]>>();

function getSharedFilters(objectApiName: string): Promise<Filter[]> {
	const cached = sharedFiltersCache.get(objectApiName);
	if (cached) return Promise.resolve(cached);
	const inFlight = sharedFiltersInFlight.get(objectApiName);
	if (inFlight) return inFlight;
	const promise = objectInfoService
		.getObjectListFilters(objectApiName)
		.then((filters) => {
			sharedFiltersCache.set(objectApiName, filters);
			sharedFiltersInFlight.delete(objectApiName);
			return filters;
		})
		.catch((err) => {
			sharedFiltersInFlight.delete(objectApiName);
			throw err;
		});
	sharedFiltersInFlight.set(objectApiName, promise);
	return promise;
}

// --- Shared Types ---
export interface FiltersData {
	filters: Filter[];
	picklistValues: Record<string, PicklistValue[]>;
	loading: boolean;
	error: string | null;
}

/**
 * Derives column definitions from filter definitions for list/result UI.
 */
function filtersToColumns(filters: Filter[]): Column[] {
	return filters.map((f) => ({
		fieldApiName: f.targetFieldPath,
		label: f.label,
		searchable: true,
		sortable: true,
	}));
}

export interface ObjectListMetadata {
	columns: Column[];
	filters: Filter[];
	picklistValues: Record<string, PicklistValue[]>;
	loading: boolean;
	error: string | null;
}

/**
 * Single hook for list-view metadata: filters (shared API), derived columns, and picklist values.
 * Use this in list/search pages to avoid duplicate useObjectColumns + useObjectFilters and duplicate state.
 */
export function useObjectListMetadata(objectApiName: string | null): ObjectListMetadata {
	const [state, setState] = useState<{
		columns: Column[];
		filters: Filter[];
		picklistValues: Record<string, PicklistValue[]>;
		loading: boolean;
		error: string | null;
	}>({
		columns: [],
		filters: [],
		picklistValues: {},
		loading: true,
		error: null,
	});

	useEffect(() => {
		if (!objectApiName) {
			setState((s) => ({ ...s, loading: false, error: "Invalid object" }));
			return;
		}

		let isCancelled = false;

		const run = async () => {
			setState((s) => ({ ...s, loading: true, error: null }));
			try {
				const filters = await getSharedFilters(objectApiName!);
				if (isCancelled) return;

				const selectFilters = filters.filter((f) => f.affordance?.toLowerCase() === "select");
				const picklistPromises = selectFilters.map((f) =>
					objectInfoService
						.getPicklistValues(objectApiName!, f.targetFieldPath)
						.then((values) => ({ fieldPath: f.targetFieldPath, values }))
						.catch(() => ({ fieldPath: f.targetFieldPath, values: [] as PicklistValue[] })),
				);
				const picklistResults = await Promise.all(picklistPromises);
				if (isCancelled) return;

				const picklistValues: Record<string, PicklistValue[]> = {};
				picklistResults.forEach(({ fieldPath, values }) => {
					picklistValues[fieldPath] = values;
				});

				setState({
					columns: filtersToColumns(filters),
					filters,
					picklistValues,
					loading: false,
					error: null,
				});
			} catch (err) {
				if (isCancelled) return;
				setState((s) => ({
					...s,
					columns: [],
					filters: [],
					picklistValues: {},
					loading: false,
					error: "Failed to load list metadata",
				}));
			}
		};

		run();
		return () => {
			isCancelled = true;
		};
	}, [objectApiName]);

	return state;
}

/**
 * Hook: useObjectColumns
 * Thin wrapper over useObjectListMetadata for backward compatibility.
 */
export function useObjectColumns(objectApiName: string | null) {
	const { columns, loading, error } = useObjectListMetadata(objectApiName);
	return {
		columns: objectApiName ? columns : [],
		columnsLoading: loading,
		columnsError: error,
	};
}

/**
 * Hook: useObjectFilters
 * Thin wrapper over useObjectListMetadata for backward compatibility.
 */
export function useObjectFilters(objectApiName: string | null) {
	const { filters, picklistValues, loading, error } = useObjectListMetadata(objectApiName);
	const filtersData: Record<string, FiltersData> = objectApiName
		? {
				[objectApiName]: {
					filters,
					picklistValues,
					loading,
					error,
				},
			}
		: {};
	return { filtersData };
}
