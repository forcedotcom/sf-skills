/**
 * Builds a single multi-aliased GraphQL document for search.
 *
 * Each SObject source becomes one aliased child of `uiapi.query`, with its own
 * `first / after / where / orderBy` variables. Variable names are
 * `${sourceKey}_first` etc. so two sources with similar names never collide.
 *
 * Selection sets are generated from `displayFields`:
 *   - string `"Name"` → `Name @optional { value displayValue }`
 *   - `{ name, raw: true }` → `Name`
 *   - `{ name, subfields }` → nested `Name @optional { ... }`
 *
 * The `idField` (default "Id") is always emitted; it is **not** wrapped
 * because uiapi's Id is a scalar.
 */

import { buildFilter, buildGlobalQueryClause, type ActiveFilterValue } from "./utils/filterUtils";
import { buildOrderBy, type SortState } from "./utils/sortUtils";
import type { DisplayField, SObjectSourceConfig } from "./types";

const KEY_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

function assertValidKey(key: string): void {
	if (!KEY_PATTERN.test(key)) {
		throw new Error(
			`Invalid source key "${key}". Must match /^[A-Za-z_][A-Za-z0-9_]*$/ to be a valid GraphQL alias and variable prefix.`,
		);
	}
}

export interface SearchQueryPayload {
	document: string;
	variables: Record<string, unknown>;
}

export interface SourceRequest {
	source: SObjectSourceConfig;
	q: string;
	filters: ActiveFilterValue[];
	sort: SortState | null;
	pageSize: number;
	afterCursor: string | undefined;
}

/**
 * Combines a per-source structured-filter clause with the global-q `or` clause.
 * Returns `undefined` when neither side has any constraints.
 */
function buildSourceWhere(
	source: SObjectSourceConfig,
	q: string,
	filters: ActiveFilterValue[],
): unknown {
	const clauses: unknown[] = [];
	const globalClause = buildGlobalQueryClause(q, source.searchableFields);
	if (globalClause) clauses.push(globalClause);
	const structured = buildFilter(filters, source.filterBy ?? []);
	if (structured) clauses.push(structured);
	if (clauses.length === 0) return undefined;
	if (clauses.length === 1) return clauses[0];
	return { and: clauses };
}

/** Builds the multi-aliased query document and a flat variables map. */
export function buildSearchQuery(requests: SourceRequest[]): SearchQueryPayload {
	if (requests.length === 0) {
		throw new Error("buildSearchQuery requires at least one source request");
	}

	const variableDeclarations: string[] = [];
	const querySelections: string[] = [];
	const variables: Record<string, unknown> = {};

	for (const request of requests) {
		const { source } = request;
		assertValidKey(source.key);

		const firstVar = `${source.key}_first`;
		const afterVar = `${source.key}_after`;
		const whereVar = `${source.key}_where`;
		const orderByVar = `${source.key}_orderBy`;
		const whereType = source.whereTypeName ?? `${source.objectName}_Filter`;
		const orderByType = source.orderByTypeName ?? `${source.objectName}_OrderBy`;

		variableDeclarations.push(
			`$${firstVar}: Int`,
			`$${afterVar}: String`,
			`$${whereVar}: ${whereType}`,
			`$${orderByVar}: ${orderByType}`,
		);

		querySelections.push(
			`${source.key}: ${source.objectName}(` +
				`first: $${firstVar}, ` +
				`after: $${afterVar}, ` +
				`where: $${whereVar}, ` +
				`orderBy: $${orderByVar}` +
				`) {\n` +
				buildSelectionBody(source) +
				`\n}`,
		);

		variables[firstVar] = request.pageSize;
		variables[afterVar] = request.afterCursor ?? null;
		variables[whereVar] = buildSourceWhere(source, request.q, request.filters) ?? null;
		variables[orderByVar] = buildOrderBy(request.sort) ?? null;
	}

	const document =
		`query Search(${variableDeclarations.join(", ")}) {\n` +
		`  uiapi {\n` +
		`    query {\n` +
		querySelections.map((s) => indent(s, "      ")).join("\n") +
		`\n    }\n` +
		`  }\n` +
		`}\n`;

	return { document, variables };
}

function buildSelectionBody(source: SObjectSourceConfig): string {
	const idField = source.idField ?? "Id";
	const fieldLines = [`    ${idField}`];
	for (const field of source.displayFields) {
		fieldLines.push(...renderField(field, "    "));
	}
	return [
		`  edges { node {`,
		...fieldLines,
		`  } }`,
		`  pageInfo { hasNextPage hasPreviousPage startCursor endCursor }`,
		`  totalCount`,
	].join("\n");
}

function renderField(field: DisplayField, indentStr: string): string[] {
	if (typeof field === "string") {
		return [`${indentStr}${field} @optional { value displayValue }`];
	}
	if ("raw" in field) {
		return [`${indentStr}${field.name}`];
	}
	const lines = [`${indentStr}${field.name} @optional {`];
	for (const sub of field.subfields) {
		lines.push(...renderField(sub, indentStr + "  "));
	}
	lines.push(`${indentStr}}`);
	return lines;
}

function indent(s: string, prefix: string): string {
	return s
		.split("\n")
		.map((line) => prefix + line)
		.join("\n");
}
