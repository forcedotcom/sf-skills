/** Filter state transformations: URL param serialization and GraphQL where-clause building. */

import type { SortState } from "./sortUtils";

export type FilterFieldType =
	| "text"
	| "picklist"
	| "numeric"
	| "boolean"
	| "date"
	| "daterange"
	| "datetime"
	| "datetimerange"
	| "multipicklist"
	| "search";

export type FilterFieldConfig<TFieldName extends string = string> = {
	field: TFieldName;
	label: string;
	type: FilterFieldType;
	placeholder?: string;
	/** Required for picklist type. */
	options?: Array<{ value: string; label: string }>;
	helpText?: string;
	/** Required for search type — the fields to match against with `or`. */
	searchFields?: string[];
};

export type ActiveFilterValue<TFieldName extends string = string> = {
	field: TFieldName;
	label: string;
	type: FilterFieldType;
	value?: string;
	min?: string;
	max?: string;
};

// ---------------------------------------------------------------------------
// URL Serialization
// ---------------------------------------------------------------------------

/** Prefix applied to all filter-related URL search param keys. */
const FILTER_PREFIX = "f.";

/** URL param key for the multi-field search term. */
const SEARCH_KEY = "q";

/** URL param key for the currently sorted field name. */
const SORT_KEY = "sort";

/** URL param key for the sort direction (ASC or DESC). */
const DIR_KEY = "dir";

/** URL param key for the page size preference. */
const PAGE_SIZE_KEY = "ps";
const PAGE_KEY = "page";

/** Serializes filter and sort state into URLSearchParams so search criteria can be bookmarked and shared. */
export function filtersToSearchParams(
	filters: ActiveFilterValue[],
	sort: SortState | null,
	pageSize?: number,
	pageIndex?: number,
): URLSearchParams {
	const params = new URLSearchParams();

	for (const filter of filters) {
		if (filter.type === "search") {
			if (filter.value) params.set(SEARCH_KEY, filter.value);
			continue;
		}
		if (filter.value !== undefined && filter.value !== "") {
			params.set(`${FILTER_PREFIX}${filter.field}`, filter.value);
		}
		if (filter.min !== undefined && filter.min !== "") {
			params.set(`${FILTER_PREFIX}${filter.field}.min`, filter.min);
		}
		if (filter.max !== undefined && filter.max !== "") {
			params.set(`${FILTER_PREFIX}${filter.field}.max`, filter.max);
		}
	}

	if (sort) {
		params.set(SORT_KEY, sort.field);
		params.set(DIR_KEY, sort.direction);
	}

	if (pageSize !== undefined) {
		params.set(PAGE_SIZE_KEY, String(pageSize));
	}

	if (pageIndex !== undefined && pageIndex > 0) {
		params.set(PAGE_KEY, String(pageIndex + 1));
	}

	return params;
}

/** Deserializes URLSearchParams back into filter and sort state, ignoring params that don't match a known config. */
export function searchParamsToFilters(
	params: URLSearchParams,
	configs: FilterFieldConfig[],
): {
	filters: ActiveFilterValue[];
	sort: SortState | null;
	pageSize: number | undefined;
	pageIndex: number;
} {
	const filters: ActiveFilterValue[] = [];

	for (const config of configs) {
		const { field, label, type } = config;

		if (type === "search") {
			const q = params.get(SEARCH_KEY);
			if (q) {
				filters.push({ field, label, type: "search", value: q });
			}
			continue;
		}

		const value = params.get(`${FILTER_PREFIX}${field}`) ?? undefined;
		const min = params.get(`${FILTER_PREFIX}${field}.min`) ?? undefined;
		const max = params.get(`${FILTER_PREFIX}${field}.max`) ?? undefined;

		const hasValue = value !== undefined && value !== "";
		const hasRange = (min !== undefined && min !== "") || (max !== undefined && max !== "");

		if (hasValue || hasRange) {
			filters.push({ field, label, type, value, min, max });
		}
	}

	let sort: SortState | null = null;
	const sortField = params.get(SORT_KEY);
	const sortDir = params.get(DIR_KEY);
	if (sortField) {
		sort = {
			field: sortField,
			direction: sortDir === "DESC" ? "DESC" : "ASC",
		};
	}

	const pageSizeRaw = params.get(PAGE_SIZE_KEY);
	const pageSize = pageSizeRaw ? parseInt(pageSizeRaw, 10) : undefined;

	const pageRaw = params.get(PAGE_KEY);
	const page = pageRaw ? parseInt(pageRaw, 10) : 1;
	const pageIndex = !isNaN(page) && page > 1 ? page - 1 : 0;

	return {
		filters,
		sort,
		pageSize: pageSize && !isNaN(pageSize) ? pageSize : undefined,
		pageIndex,
	};
}

// ---------------------------------------------------------------------------
// GraphQL Filter Building
// ---------------------------------------------------------------------------

/** Combines active filters into a single GraphQL where clause, ANDing multiple filters together. */
export function buildFilter<TFilter>(
	filters: ActiveFilterValue[],
	configs: FilterFieldConfig[],
): TFilter | undefined {
	const configMap = new Map(configs.map((c) => [c.field, c]));
	const clauses: TFilter[] = [];

	for (const filter of filters) {
		const clause = buildSingleFilter<TFilter>(filter, configMap.get(filter.field));
		if (clause) clauses.push(clause);
	}

	if (clauses.length === 0) return undefined;
	if (clauses.length === 1) return clauses[0];
	return { and: clauses } as TFilter;
}

/** Converts a YYYY-MM-DD date string to an ISO-8601 datetime at midnight UTC (inclusive lower bound). */
function toStartOfDay(dateStr: string): string {
	return `${dateStr}T00:00:00.000Z`;
}

/** Converts a YYYY-MM-DD date string to an ISO-8601 datetime at the last millisecond of the day UTC (inclusive upper bound). */
function toEndOfDay(dateStr: string): string {
	return `${dateStr}T23:59:59.999Z`;
}

/** Converts a single active filter value into a GraphQL filter clause based on its type. */
function buildSingleFilter<TFilter>(
	filter: ActiveFilterValue,
	config?: FilterFieldConfig,
): TFilter | null {
	const { field, type, value, min, max } = filter;

	switch (type) {
		case "text": {
			if (!value) return null;
			return { [field]: { like: `%${value}%` } } as TFilter;
		}
		case "picklist": {
			if (!value) return null;
			return { [field]: { eq: value } } as TFilter;
		}
		case "numeric": {
			if (!min && !max) return null;
			const ops: Record<string, number> = {};
			if (min) ops.gte = Number(min);
			if (max) ops.lte = Number(max);
			return { [field]: ops } as TFilter;
		}
		case "boolean": {
			if (value === undefined || value === "") return null;
			return { [field]: { eq: value === "true" } } as TFilter;
		}
		case "multipicklist": {
			if (!value) return null;
			const values = value.split(",");
			if (values.length === 1) {
				return { [field]: { eq: values[0] } } as TFilter;
			}
			return { [field]: { in: values } } as TFilter;
		}
		case "date": {
			if (!min && !max) return null;
			const op = value ?? (min ? "gte" : "lte");
			const dateStr = min ?? max;
			return { [field]: { [op]: { value: dateStr } } } as TFilter;
		}
		case "daterange": {
			if (!min && !max) return null;
			const clauses: TFilter[] = [];
			if (min) {
				clauses.push({
					[field]: { gte: { value: min } },
				} as TFilter);
			}
			if (max) {
				clauses.push({
					[field]: { lte: { value: max } },
				} as TFilter);
			}
			return clauses.length === 1 ? clauses[0] : ({ and: clauses } as TFilter);
		}
		case "datetime": {
			if (!min && !max) return null;
			const op = value ?? (min ? "gte" : "lte");
			const dateStr = min ?? max;
			const isoStr = op === "gte" || op === "gt" ? toStartOfDay(dateStr!) : toEndOfDay(dateStr!);
			return { [field]: { [op]: { value: isoStr } } } as TFilter;
		}
		case "datetimerange": {
			if (!min && !max) return null;
			const clauses: TFilter[] = [];
			if (min) {
				clauses.push({
					[field]: { gte: { value: toStartOfDay(min) } },
				} as TFilter);
			}
			if (max) {
				clauses.push({
					[field]: { lte: { value: toEndOfDay(max) } },
				} as TFilter);
			}
			return clauses.length === 1 ? clauses[0] : ({ and: clauses } as TFilter);
		}
		case "search": {
			if (!value) return null;
			const searchFields = config?.searchFields ?? [];
			if (searchFields.length === 0) return null;
			// Supports dot-notation for relationship fields (e.g. "User__r.Name")
			// by building nested filter objects: { User__r: { Name: { like: "%x%" } } }
			const clauses = searchFields.map((f) => {
				const parts = f.split(".");
				let clause: Record<string, unknown> = { like: `%${value}%` };
				for (let i = parts.length - 1; i >= 0; i--) {
					clause = { [parts[i]]: clause };
				}
				return clause as TFilter;
			});
			if (clauses.length === 1) return clauses[0];
			return { or: clauses } as TFilter;
		}
		default:
			return null;
	}
}
