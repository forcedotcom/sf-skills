/**
 * Filter primitives for search.
 *
 * Two responsibilities:
 *   1. Build a GraphQL `where` clause from a list of active filter values.
 *   2. Serialize/deserialize active filters to/from URLSearchParams under a
 *      per-source namespace prefix (so multiple sources can coexist on one URL).
 *
 * The URL helpers are namespaced: each source declares its key, and filter
 * params are written as `s.<key>.f.<field>=...`. Sort uses
 * `s.<key>.sort=<field>&s.<key>.dir=ASC|DESC`. Page size and page index use
 * `s.<key>.ps=<size>` and `s.<key>.page=<n>`.
 *
 * The global search term `q=...` is **not** scoped to a source — it's broadcast
 * to every source's `searchableFields` by the query builder.
 */

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
	| "multipicklist";

/**
 * Which comparison UI a date/datetime filter exposes:
 *   - `"range"`: a single Between control (two date inputs, lower–upper bound).
 *   - `"comparison"`: an After / Before selector with one date input.
 *   - `"both"`: a Between / After / Before selector that switches between the two.
 *
 * Applies only to the date-family `type`s (`date`, `daterange`, `datetime`,
 * `datetimerange`); ignored for other field types. Defaults to `"comparison"`.
 */
export type DateFilterMode = "range" | "comparison" | "both";

export type FilterFieldConfig<TFieldName extends string = string> = {
	field: TFieldName;
	label: string;
	type: FilterFieldType;
	placeholder?: string;
	/** Required for picklist / multipicklist. */
	options?: Array<{ value: string; label: string }>;
	/** Date-family only — see {@link DateFilterMode}. Defaults to `"comparison"`. */
	dateMode?: DateFilterMode;
	helpText?: string;
	// Numeric-family only.
	min?: number;
	max?: number;
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
// URL serialization (per-source namespace)
// ---------------------------------------------------------------------------

const SOURCE_PREFIX = "s.";
const FILTER_INFIX = ".f.";
const SORT_SUFFIX = ".sort";
const DIR_SUFFIX = ".dir";
const PAGE_SIZE_SUFFIX = ".ps";
const PAGE_SUFFIX = ".page";

/** Global search term key (not source-scoped). */
export const GLOBAL_QUERY_KEY = "q";

function filterKey(sourceKey: string, field: string, suffix?: string) {
	return `${SOURCE_PREFIX}${sourceKey}${FILTER_INFIX}${field}${suffix ? `.${suffix}` : ""}`;
}

/**
 * The source's own default sort / page size. When a source's current state
 * matches these, the corresponding URL params are omitted so the query string
 * only ever reflects an *explicit* user choice — resetting filters or returning
 * a source to its defaults yields a clean URL instead of one littered with the
 * defaults. The read path falls back to these same defaults when the params are
 * absent, so the round-trip is lossless.
 */
export interface SourceParamDefaults {
	sort?: SortState | null;
	pageSize?: number;
}

function sortMatchesDefault(sort: SortState, defaultSort: SortState | null | undefined): boolean {
	return (
		!!defaultSort && sort.field === defaultSort.field && sort.direction === defaultSort.direction
	);
}

export function writeSourceParams(
	params: URLSearchParams,
	sourceKey: string,
	filters: ActiveFilterValue[],
	sort: SortState | null,
	pageSize?: number,
	pageIndex?: number,
	defaults?: SourceParamDefaults,
): void {
	for (const filter of filters) {
		if (filter.value !== undefined && filter.value !== "") {
			params.set(filterKey(sourceKey, filter.field), filter.value);
		}
		if (filter.min !== undefined && filter.min !== "") {
			params.set(filterKey(sourceKey, filter.field, "min"), filter.min);
		}
		if (filter.max !== undefined && filter.max !== "") {
			params.set(filterKey(sourceKey, filter.field, "max"), filter.max);
		}
	}
	// Only serialize sort when it differs from the source default — otherwise
	// the URL would carry the default the user never chose.
	if (sort && !sortMatchesDefault(sort, defaults?.sort)) {
		params.set(`${SOURCE_PREFIX}${sourceKey}${SORT_SUFFIX}`, sort.field);
		params.set(`${SOURCE_PREFIX}${sourceKey}${DIR_SUFFIX}`, sort.direction);
	}
	if (pageSize !== undefined && pageSize !== defaults?.pageSize) {
		params.set(`${SOURCE_PREFIX}${sourceKey}${PAGE_SIZE_SUFFIX}`, String(pageSize));
	}
	if (pageIndex !== undefined && pageIndex > 0) {
		params.set(`${SOURCE_PREFIX}${sourceKey}${PAGE_SUFFIX}`, String(pageIndex + 1));
	}
}

export interface ReadSourceParamsResult {
	filters: ActiveFilterValue[];
	sort: SortState | null;
	pageSize: number | undefined;
	pageIndex: number;
}

export function readSourceParams(
	params: URLSearchParams,
	sourceKey: string,
	configs: FilterFieldConfig[],
): ReadSourceParamsResult {
	const filters: ActiveFilterValue[] = [];
	for (const config of configs) {
		const { field, label, type } = config;
		const value = params.get(filterKey(sourceKey, field)) ?? undefined;
		const min = params.get(filterKey(sourceKey, field, "min")) ?? undefined;
		const max = params.get(filterKey(sourceKey, field, "max")) ?? undefined;

		const hasValue = value !== undefined && value !== "";
		const hasRange = (min !== undefined && min !== "") || (max !== undefined && max !== "");
		if (hasValue || hasRange) {
			filters.push({ field, label, type, value, min, max });
		}
	}

	let sort: SortState | null = null;
	const sortField = params.get(`${SOURCE_PREFIX}${sourceKey}${SORT_SUFFIX}`);
	const sortDir = params.get(`${SOURCE_PREFIX}${sourceKey}${DIR_SUFFIX}`);
	if (sortField) {
		sort = { field: sortField, direction: sortDir === "DESC" ? "DESC" : "ASC" };
	}

	const pageSizeRaw = params.get(`${SOURCE_PREFIX}${sourceKey}${PAGE_SIZE_SUFFIX}`);
	const pageSize = pageSizeRaw ? parseInt(pageSizeRaw, 10) : undefined;
	const pageRaw = params.get(`${SOURCE_PREFIX}${sourceKey}${PAGE_SUFFIX}`);
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
// GraphQL filter building
// ---------------------------------------------------------------------------

/**
 * Combines active filter values into a GraphQL `where` clause for one source.
 * Returns `undefined` when no constraints are active.
 */
export function buildFilter(filters: ActiveFilterValue[], configs: FilterFieldConfig[]): unknown {
	const configMap = new Map(configs.map((c) => [c.field, c]));
	const clauses: unknown[] = [];
	for (const filter of filters) {
		const clause = buildSingleFilter(filter, configMap.get(filter.field));
		if (clause) clauses.push(clause);
	}
	if (clauses.length === 0) return undefined;
	if (clauses.length === 1) return clauses[0];
	return { and: clauses };
}

function toStartOfDay(d: string) {
	return `${d}T00:00:00.000Z`;
}
function toEndOfDay(d: string) {
	return `${d}T23:59:59.999Z`;
}

/** Escapes LIKE metacharacters (`\`, `%`, `_`) so user input is matched literally. */
function escapeLikePattern(value: string): string {
	return value.replace(/[\\%_]/g, "\\$&");
}

function buildSingleFilter(filter: ActiveFilterValue, config?: FilterFieldConfig): unknown {
	const { field, type, value, min, max } = filter;
	switch (type) {
		case "text": {
			if (!value) return null;
			return { [field]: { like: `%${escapeLikePattern(value)}%` } };
		}
		case "picklist": {
			if (!value) return null;
			return { [field]: { eq: value } };
		}
		case "numeric": {
			if (!min && !max) return null;
			const ops: Record<string, number> = {};
			// clamp both endpoints into the declared [min,max] bounds
			const clamp = (n: number) => {
				if (config?.min != null) n = Math.max(n, config.min);
				if (config?.max != null) n = Math.min(n, config.max);
				return n;
			};
			// Drop any endpoint that isn't finite — NaN/Infinity serialize to null on the wire.
			const lo = Number(min);
			if (min && Number.isFinite(lo)) ops.gte = clamp(lo);
			const hi = Number(max);
			if (max && Number.isFinite(hi)) ops.lte = clamp(hi);
			// If both endpoints were dropped as invalid, emit no clause at all.
			if (Object.keys(ops).length === 0) return null;
			return { [field]: ops };
		}
		case "boolean": {
			if (value === undefined || value === "") return null;
			return { [field]: { eq: value === "true" } };
		}
		case "multipicklist": {
			if (!value) return null;
			const values = value.split(",").filter(Boolean);
			if (values.length === 0) return null;
			if (values.length === 1) return { [field]: { eq: values[0] } };
			return { [field]: { in: values } };
		}
		case "date": {
			if (!min && !max) return null;
			const op = min ? "gte" : "lte";
			const dateStr = min ?? max;
			return { [field]: { [op]: { value: dateStr } } };
		}
		case "daterange": {
			if (!min && !max) return null;
			const clauses: unknown[] = [];
			if (min) clauses.push({ [field]: { gte: { value: min } } });
			if (max) clauses.push({ [field]: { lte: { value: max } } });
			return clauses.length === 1 ? clauses[0] : { and: clauses };
		}
		case "datetime": {
			if (!min && !max) return null;
			const op = min ? "gte" : "lte";
			const dateStr = min ?? max;
			const isoStr = op === "gte" ? toStartOfDay(dateStr!) : toEndOfDay(dateStr!);
			return { [field]: { [op]: { value: isoStr } } };
		}
		case "datetimerange": {
			if (!min && !max) return null;
			const clauses: unknown[] = [];
			if (min) clauses.push({ [field]: { gte: { value: toStartOfDay(min) } } });
			if (max) clauses.push({ [field]: { lte: { value: toEndOfDay(max) } } });
			return clauses.length === 1 ? clauses[0] : { and: clauses };
		}
		default:
			return null;
	}
}

/**
 * Builds a global-q `or` clause across the source's searchable fields.
 * Returns `undefined` when q is empty or the source has no searchable fields.
 */
export function buildGlobalQueryClause(q: string, searchableFields: string[]): unknown {
	const trimmed = q.trim();
	if (!trimmed || searchableFields.length === 0) return undefined;
	const clauses = searchableFields.map((path) => {
		const parts = path.split(".");
		let clause: Record<string, unknown> = { like: `%${escapeLikePattern(trimmed)}%` };
		for (let i = parts.length - 1; i >= 0; i--) {
			clause = { [parts[i]]: clause };
		}
		return clause;
	});
	return clauses.length === 1 ? clauses[0] : { or: clauses };
}
