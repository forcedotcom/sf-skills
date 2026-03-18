/**
 * Record GraphQL Service
 *
 * Single service for querying Salesforce object records via GraphQL UI API (uiapi.query).
 * Handles both list (paginated, filter, sort, search) and single-record-by-id using one query shape.
 *
 * @module api/recordListGraphQLService
 */

import { createDataSDK } from "@salesforce/sdk-data";
import type { Column } from "../types/search/searchResults";
import type { FilterCriteria } from "../types/filters/filters";

const DEFAULT_PAGE_SIZE = 50;

/** Tree of selection: leaf is "value", branch is nested fields. Keys starting with __on_ are inline fragments (e.g. __on_User). */
interface SelectionTree {
	[key: string]: "value" | SelectionTree;
}

/**
 * Polymorphic relationship fields and the concrete GraphQL types they can resolve to.
 * Only relationship names listed here use inline fragments; others use direct selection
 * (e.g. Parent -> Parent { Name { value } } because "Parent" is not a schema type).
 * We use a single fragment per field to avoid schema validation errors (e.g. User and Group
 * cannot both be spread in the same selection in some contexts).
 */
const POLYMORPHIC_RELATIONSHIP_TYPES: Record<string, string[]> = {
	Owner: ["User"],
	CreatedBy: ["User"],
	LastModifiedBy: ["User"],
};

/**
 * Builds a selection tree from columns (fieldApiName). Simple fields (e.g. Name, OwnerId) become
 * top-level leaves. Relationship fields that are in POLYMORPHIC_RELATIONSHIP_TYPES use a single
 * inline fragment on the first concrete type (e.g. ... on User). All other relationship fields
 * (e.g. Parent, Account) use direct selection (e.g. Parent { Name { value } }) because the
 * relationship name is not necessarily a GraphQL type name (e.g. Parent resolves to Account).
 */
function buildSelectionTree(columns: Column[]): SelectionTree {
	const allFieldNames = new Set(columns.map((c) => (c.fieldApiName ?? "").trim()).filter(Boolean));
	const tree: SelectionTree = { Id: "value" };
	for (const col of columns) {
		const name = (col.fieldApiName ?? "").trim();
		if (!name) continue;
		const parts = name.split(".");
		if (parts.length === 1) {
			const fieldName = parts[0];
			const hasCorrespondingId = allFieldNames.has(`${fieldName}Id`);
			if (hasCorrespondingId) {
				const knownTypes = POLYMORPHIC_RELATIONSHIP_TYPES[fieldName];
				if (knownTypes?.length) {
					// Use a single inline fragment to avoid "User can never be Group" validation errors
					const typeName = knownTypes[0];
					tree[fieldName] = { [`__on_${typeName}`]: { Name: "value" } };
				} else {
					// Relationship name (e.g. Parent) is not a GraphQL type; use direct selection
					tree[fieldName] = { Name: "value" };
				}
			} else {
				tree[fieldName] = "value";
			}
		} else {
			let current = tree;
			for (let i = 0; i < parts.length; i++) {
				const part = parts[i];
				const isLeaf = i === parts.length - 1;
				if (isLeaf) {
					current[part] = "value";
				} else {
					const existing = current[part];
					if (existing === "value") continue;
					if (!existing) {
						current[part] = {};
					}
					current = current[part] as SelectionTree;
				}
			}
		}
	}
	return tree;
}

/**
 * Serializes a selection tree to GraphQL selection set string.
 * Keys starting with __on_ are emitted as inline fragments (... on TypeName { ... }).
 * Id is scalar (no subselection); other leaves use { value }.
 */
function serializeSelectionTree(tree: SelectionTree, indent: string): string {
	const fragmentKeys = Object.keys(tree).filter((k) => k.startsWith("__on_"));
	const normalKeys = Object.keys(tree).filter((k) => !k.startsWith("__on_"));
	normalKeys.sort((a, b) => {
		if (a === "Id") return -1;
		if (b === "Id") return 1;
		return a.localeCompare(b);
	});
	fragmentKeys.sort();
	const lines: string[] = [];
	const childIndent = `${indent}  `;
	for (const key of normalKeys) {
		const val = tree[key];
		if (val === "value") {
			if (key === "Id") {
				lines.push(`${indent}Id`);
			} else {
				lines.push(`${indent}${key} { value }`);
			}
		} else {
			lines.push(`${indent}${key} {`);
			lines.push(serializeSelectionTree(val, childIndent));
			lines.push(`${indent}}`);
		}
	}
	for (const key of fragmentKeys) {
		const typeName = key.slice(5);
		const val = tree[key];
		if (val && typeof val === "object") {
			lines.push(`${indent}... on ${typeName} {`);
			lines.push(serializeSelectionTree(val, childIndent));
			lines.push(`${indent}}`);
		}
	}
	return lines.join("\n");
}

function buildNodeSelection(columns: Column[]): string {
	const tree = buildSelectionTree(columns);
	return serializeSelectionTree(tree, "            ");
}

/**
 * Builds GraphQL where clause from filter criteria and optional search text.
 * Search text is applied as Name like %query%. Multiple conditions are combined with and.
 *
 * @param criteria - Field filters (fieldPath, operator, values).
 * @param searchQuery - Optional; adds Name like %searchQuery% when provided.
 */
export function buildWhereFromCriteria(
	criteria: FilterCriteria[],
	searchQuery?: string,
): Record<string, unknown> | null {
	const conditions: Record<string, unknown>[] = [];

	if (searchQuery && searchQuery.trim()) {
		const term = `%${searchQuery.trim()}%`;
		conditions.push({ Name: { like: term } });
	}

	for (const c of criteria) {
		if (!c.fieldPath || !c.operator || !c.values?.length) continue;
		const op = c.operator;
		const parts = c.fieldPath.split(".");
		const fieldClause = op === "in" ? { in: c.values } : { [op]: c.values[0] };
		if (parts.length === 1) {
			conditions.push({ [parts[0]]: fieldClause });
		} else {
			let nested: Record<string, unknown> = { [parts[parts.length - 1]]: fieldClause };
			for (let i = parts.length - 2; i >= 0; i--) {
				nested = { [parts[i]]: nested };
			}
			conditions.push(nested);
		}
	}

	if (conditions.length === 0) return null;
	if (conditions.length === 1) return conditions[0] as Record<string, unknown>;
	return { and: conditions };
}

/**
 * Parses sortBy string (e.g. "Name", "Name ASC", "AnnualRevenue DESC") into GraphQL orderBy shape.
 * Default direction is ASC.
 */
export function buildOrderByFromSort(
	sortBy: string,
): Record<string, { order: "ASC" | "DESC" }> | null {
	const trimmed = (sortBy ?? "").trim();
	if (!trimmed || trimmed.toLowerCase() === "relevance") return null;
	const parts = trimmed.split(/\s+/);
	const field = parts[0];
	const dir = parts[1]?.toUpperCase() === "DESC" ? "DESC" : "ASC";
	return { [field]: { order: dir } };
}

/** Variables for the GetRecords GraphQL operation. */
export interface RecordListGraphQLVariables {
	first?: number;
	after?: string | null;
	where?: Record<string, unknown> | null;
	orderBy?: Record<string, unknown> | null;
}

export interface RecordListGraphQLOptions {
	objectApiName: string;
	columns: Column[];
	/** When set, fetches a single record by Id (first=1, where Id eq); used for detail view. */
	recordId?: string | null;
	first?: number;
	after?: string | null;
	filters?: FilterCriteria[];
	orderBy?: Record<string, unknown> | null;
	searchQuery?: string;
}

/**
 * Builds the GraphQL query string for uiapi.query.{objectApiName}.
 * Used for both list (pagination, where, orderBy) and single record (where Id eq, first 1).
 *
 * @param objectApiName - API name of the object (e.g. Account, Contact).
 * @param columns - Field selection (becomes node selection via buildNodeSelection).
 * @param options - Optional where and orderBy; when recordId is used, where is set to Id eq.
 */
export function buildGetRecordsQuery(
	objectApiName: string,
	columns: Column[],
	options?: { where?: Record<string, unknown> | null; orderBy?: Record<string, unknown> | null },
): string {
	const nodeSelection = buildNodeSelection(columns);
	const hasWhere = options?.where != null && Object.keys(options.where).length > 0;
	const hasOrderBy = options?.orderBy != null && Object.keys(options.orderBy).length > 0;

	const filterType = `${objectApiName}_Filter`;
	const orderByType = `${objectApiName}_OrderBy`;

	const varDecls = [
		"$first: Int",
		"$after: String",
		...(hasWhere ? [`$where: ${filterType}`] : []),
		...(hasOrderBy ? [`$orderBy: ${orderByType}`] : []),
	];
	const opArgs = [
		"first: $first",
		"after: $after",
		...(hasWhere ? ["where: $where"] : []),
		...(hasOrderBy ? ["orderBy: $orderBy"] : []),
	];

	return `query GetRecords(${varDecls.join(", ")}) {
  uiapi {
    query {
      ${objectApiName}(${opArgs.join(", ")}) {
        edges {
          node {
            ${nodeSelection}
          }
        }
        pageInfo {
          hasNextPage
          hasPreviousPage
          endCursor
          startCursor
        },
		totalCount,
		pageResultCount
      }
    }
  }
}`;
}

export interface RecordListGraphQLResult {
	uiapi?: {
		query?: {
			[key: string]: {
				edges?: Array<{ node?: Record<string, unknown> }>;
				pageInfo?: {
					hasNextPage?: boolean;
					hasPreviousPage?: boolean;
					endCursor?: string | null;
					startCursor?: string | null;
				};
			};
		};
	};
}

/** GraphQL node shape for a single record (Id + field selections with value/nested). */
export type GraphQLRecordNode = Record<string, unknown>;

/**
 * Fetches records for the given object via GraphQL (single query for both list and single record).
 *
 * - List: pass first, after, filters, orderBy, searchQuery.
 * - Single record: pass recordId; first is set to 1 and where includes Id eq.
 *
 * @param options.objectApiName - API name of the object (e.g. Account, Contact).
 * @param options.columns - Field selection (from filters-derived columns or layout-derived optionalFields).
 * @param options.recordId - If set, fetches one record by Id (first=1, where Id eq).
 * @param options.first - Page size (default 50; ignored when recordId is set).
 * @param options.after - Cursor for next page.
 * @param options.filters - Filter criteria (mapped to where).
 * @param options.orderBy - GraphQL orderBy; use buildOrderByFromSort(sortBy) when needed.
 * @param options.searchQuery - Text search (Name like %query% in where).
 * @returns Connection result (edges, pageInfo); for recordId callers use edges[0].node.
 */
export async function getRecordsGraphQL(
	options: RecordListGraphQLOptions,
): Promise<RecordListGraphQLResult> {
	const {
		objectApiName,
		columns,
		recordId,
		first = DEFAULT_PAGE_SIZE,
		after = null,
		filters = [],
		orderBy = null,
		searchQuery,
	} = options;

	const listWhere = buildWhereFromCriteria(filters, searchQuery);
	const where =
		recordId != null && recordId !== ""
			? listWhere != null && Object.keys(listWhere).length > 0
				? { and: [{ Id: { eq: recordId } }, listWhere] }
				: { Id: { eq: recordId } }
			: listWhere;
	const effectiveFirst = recordId != null && recordId !== "" ? 1 : first;
	const hasWhere = where != null && Object.keys(where).length > 0;
	const hasOrderBy = orderBy != null && Object.keys(orderBy).length > 0;

	const query = buildGetRecordsQuery(objectApiName, columns, { where, orderBy });
	const variables: Record<string, unknown> = {
		first: effectiveFirst,
		after: after ?? null,
		...(hasWhere && where ? { where } : {}),
		...(hasOrderBy && orderBy ? { orderBy } : {}),
	};

	const data = await createDataSDK();
	const response = await data.graphql?.<RecordListGraphQLResult>(query, variables);

	if (response?.errors?.length) {
		const errorMessages = response.errors.map((e) => e.message).join("; ");
		throw new Error(`GraphQL Error: ${errorMessages}`);
	}

	return response?.data ?? ({} as RecordListGraphQLResult);
}

/**
 * Fetches a single record by Id. Uses the same GraphQL query as list (getRecordsGraphQL with recordId + first 1).
 *
 * @param objectApiName - API name of the object.
 * @param recordId - Record Id.
 * @param columns - Field selection (e.g. layout-derived optionalFields as Column[]).
 * @returns The record node or null if not found.
 */
export async function getRecordByIdGraphQL(
	objectApiName: string,
	recordId: string,
	columns: Column[],
): Promise<GraphQLRecordNode | null> {
	const result = await getRecordsGraphQL({
		objectApiName,
		columns,
		recordId,
		first: 1,
	});
	const edges =
		result?.uiapi?.query?.[objectApiName]?.edges ??
		([] as Array<{ node?: Record<string, unknown> }>);
	return (edges[0]?.node ?? null) as GraphQLRecordNode | null;
}
