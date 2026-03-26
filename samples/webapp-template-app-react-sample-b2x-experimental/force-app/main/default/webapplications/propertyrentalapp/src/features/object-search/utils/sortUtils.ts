import { ResultOrder, NullOrder } from "../../../api/graphql-operations-types";

export type SortFieldConfig<TFieldName extends string = string> = {
	field: TFieldName;
	label: string;
};

export type SortState<TFieldName extends string = string> = {
	field: TFieldName;
	direction: "ASC" | "DESC";
};

/**
 * Converts a {@link SortState} into a GraphQL order-by object.
 *
 * @typeParam TOrderBy - The GraphQL order-by input type (e.g. `AccountOrderByInput`).
 * @param sort - The current sort state from the UI, or `null` if no sort is applied.
 * @returns An order-by object for the GraphQL query's `orderBy` variable, or
 *          `undefined` if no sort is active (which uses the API's default ordering).
 *
 * @example
 * ```ts
 * const orderBy = buildOrderBy<AccountOrderByInput>({
 *   field: "Name",
 *   direction: "ASC",
 * });
 * // orderBy => { Name: { order: ResultOrder.Asc, nulls: NullOrder.Last } }
 * ```
 */
export function buildOrderBy<TOrderBy>(sort: SortState | null): TOrderBy | undefined {
	if (!sort) return undefined;
	return {
		[sort.field]: {
			order: sort.direction === "ASC" ? ResultOrder.Asc : ResultOrder.Desc,
			nulls: NullOrder.Last,
		},
	} as TOrderBy;
}
