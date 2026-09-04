import { ResultOrder, NullOrder } from "../../../api/graphql-operations-types";

export type SortFieldConfig<TFieldName extends string = string> = {
	field: TFieldName;
	label: string;
};

export type SortState<TFieldName extends string = string> = {
	field: TFieldName;
	direction: "ASC" | "DESC";
};

/** Converts a SortState into a GraphQL order-by object, or undefined if no sort is active. */
export function buildOrderBy<TOrderBy>(sort: SortState | null): TOrderBy | undefined {
	if (!sort) return undefined;
	return {
		[sort.field]: {
			order: sort.direction === "ASC" ? ResultOrder.Asc : ResultOrder.Desc,
			nulls: NullOrder.Last,
		},
	} as TOrderBy;
}
