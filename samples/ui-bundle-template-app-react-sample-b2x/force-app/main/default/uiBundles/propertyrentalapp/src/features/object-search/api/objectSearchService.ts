import { createDataSDK } from "@salesforce/platform-sdk";

export interface ObjectSearchOptions<TWhere, TOrderBy> {
	where?: TWhere;
	orderBy?: TOrderBy;
	first?: number;
	after?: string;
}

export type PicklistOption = { value: string; label: string };

/**
 * Executes a GraphQL search query and extracts the result for the given object name
 * from the standard `uiapi.query.<ObjectName>` response shape.
 */
export async function searchObjects<TResult, TQuery, TVariables>(
	query: string,
	objectName: string,
	options: ObjectSearchOptions<unknown, unknown> = {},
): Promise<TResult> {
	const { where, orderBy, first = 20, after } = options;

	const data = await createDataSDK();
	const variables = { first, after, where, orderBy } as TVariables;
	const result = await data.graphql!.query<TQuery, TVariables>({
		query: query,
		variables: variables,
	});

	if (result.errors?.length) {
		throw new Error(result.errors.map((e) => e.message).join("; "));
	}

	const uiapi = (result.data as Record<string, unknown> | undefined)?.uiapi as
		| Record<string, unknown>
		| undefined;
	const queryResult = (uiapi?.query as Record<string, unknown> | undefined)?.[objectName] as
		| TResult
		| undefined;

	if (!queryResult) {
		throw new Error(`No ${objectName} data returned`);
	}

	return queryResult;
}

/**
 * Executes a GraphQL aggregate/groupBy query and extracts picklist options
 * from the standard `uiapi.aggregate.<ObjectName>` response shape.
 */
export async function fetchDistinctValues<TQuery>(
	query: string,
	objectName: string,
	fieldName: string,
): Promise<PicklistOption[]> {
	const data = await createDataSDK();
	const result = await data.graphql!.query<TQuery>({ query: query });

	if (result.errors?.length) {
		throw new Error(result.errors.map((e) => e.message).join("; "));
	}

	const uiapi = (result.data as Record<string, unknown> | undefined)?.uiapi as
		| Record<string, unknown>
		| undefined;
	const aggregate = (uiapi?.aggregate as Record<string, unknown> | undefined)?.[objectName] as
		| { edges?: Array<{ node?: { aggregate?: Record<string, unknown> } }> }
		| undefined;

	const edges = aggregate?.edges ?? [];
	return edges
		.map((edge) => {
			const field = edge?.node?.aggregate?.[fieldName] as
				| { value?: string | null; displayValue?: string | null; label?: string | null }
				| undefined;
			const value = field?.value;
			if (!value) return null;
			return { value, label: field.label ?? field.displayValue ?? value };
		})
		.filter((opt): opt is PicklistOption => opt !== null);
}
