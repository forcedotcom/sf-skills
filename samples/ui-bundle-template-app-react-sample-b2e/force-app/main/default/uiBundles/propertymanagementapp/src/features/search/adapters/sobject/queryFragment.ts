/**
 * SObject fragment builder.
 *
 * Extracted verbatim from `queryBuilder.ts`: `buildSelectionBody`,
 * `renderField`, `buildSourceWhere`, `assertValidKey`, `KEY_PATTERN`, and the
 * per-source variable/selection assembly. Emits one `QueryFragmentContribution`
 * with `placement: "uiapi.query"` — the `${key}: ${objectName}(...) { … }`
 * selection, its 4 per-source variable declarations, and their 4 values.
 *
 * Behaviour is byte-for-byte equivalent to the original inline logic; this is a
 * move, not a rewrite.
 *
 * Selection sets are generated from `displayFields`:
 *   - string `"Name"` → `Name @optional { value displayValue }`
 *   - `{ name, raw: true }` → `Name`
 *   - `{ name, subfields }` → nested `Name @optional { ... }`
 *
 * The `idField` (default "Id") is always emitted; it is **not** wrapped
 * because uiapi's Id is a scalar.
 */

import {
	buildFilter,
	buildGlobalQueryClause,
	type ActiveFilterValue,
} from "../../utils/filterUtils";
import { buildOrderBy } from "../../utils/sortUtils";
import type { DisplayField, SObjectSourceConfig } from "../../types";
import type { QueryFragmentContribution, SourceRequest } from "../types";

const KEY_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

function assertValidKey(key: string): void {
	if (!KEY_PATTERN.test(key)) {
		throw new Error(
			`Invalid source key "${key}". Must match /^[A-Za-z_][A-Za-z0-9_]*$/ to be a valid GraphQL alias and variable prefix.`,
		);
	}
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

/**
 * Builds one SObject source's `QueryFragmentContribution`.
 *
 * The fragment is the `${key}: ${objectName}(...) { … }` selection that lives
 * inside `uiapi.query`; the 4 declarations/values are the per-source
 * `first / after / where / orderBy` variables. Output matches the original
 * inline builder exactly.
 */
export function buildSObjectFragment(
	request: SourceRequest<SObjectSourceConfig>,
): QueryFragmentContribution {
	const { source } = request;
	assertValidKey(source.key);

	const firstVar = `${source.key}_first`;
	const afterVar = `${source.key}_after`;
	const whereVar = `${source.key}_where`;
	const orderByVar = `${source.key}_orderBy`;
	const whereType = source.whereTypeName ?? `${source.objectName}_Filter`;
	const orderByType = source.orderByTypeName ?? `${source.objectName}_OrderBy`;

	const variableDeclarations = [
		`$${firstVar}: Int`,
		`$${afterVar}: String`,
		`$${whereVar}: ${whereType}`,
		`$${orderByVar}: ${orderByType}`,
	];

	const fragment =
		`${source.key}: ${source.objectName}(` +
		`first: $${firstVar}, ` +
		`after: $${afterVar}, ` +
		`where: $${whereVar}, ` +
		`orderBy: $${orderByVar}` +
		`) {\n` +
		buildSelectionBody(source) +
		`\n}`;

	const variables: Record<string, unknown> = {
		[firstVar]: request.pageSize,
		[afterVar]: request.afterCursor ?? null,
		[whereVar]: buildSourceWhere(source, request.q, request.filters) ?? null,
		[orderByVar]: buildOrderBy(request.sort) ?? null,
	};

	return {
		variableDeclarations,
		variables,
		placement: "uiapi.query",
		fragment,
	};
}
