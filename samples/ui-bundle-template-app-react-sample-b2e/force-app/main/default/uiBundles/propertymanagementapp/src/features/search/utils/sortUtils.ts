/**
 * Sort state and order-by builder for search.
 *
 * The order-by output shape matches the Salesforce uiapi GraphQL convention:
 *   { [field]: { order: ASC|DESC, nulls: LAST } }
 *
 * The constants are stringly-typed here (rather than imported from codegen)
 * because search builds its query at runtime and isn't tied to a
 * specific generated schema.
 */

export type SortFieldConfig<TFieldName extends string = string> = {
	field: TFieldName;
	label: string;
};

export type SortState<TFieldName extends string = string> = {
	field: TFieldName;
	direction: "ASC" | "DESC";
};

const ORDER_ASC = "ASC";
const ORDER_DESC = "DESC";
const NULLS_LAST = "LAST";

export function buildOrderBy(sort: SortState | null): unknown {
	if (!sort) return undefined;
	return {
		[sort.field]: {
			order: sort.direction === "ASC" ? ORDER_ASC : ORDER_DESC,
			nulls: NULLS_LAST,
		},
	};
}
