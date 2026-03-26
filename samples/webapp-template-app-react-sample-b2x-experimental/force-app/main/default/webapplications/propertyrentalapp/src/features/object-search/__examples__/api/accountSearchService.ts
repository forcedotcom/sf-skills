import SEARCH_ACCOUNTS_QUERY from "./query/searchAccounts.graphql?raw";
import DISTINCT_INDUSTRIES_QUERY from "./query/distinctAccountIndustries.graphql?raw";
import DISTINCT_TYPES_QUERY from "./query/distinctAccountTypes.graphql?raw";
import {
	searchObjects,
	fetchDistinctValues,
	type ObjectSearchOptions,
	type PicklistOption,
} from "../../api/objectSearchService";
import type {
	SearchAccountsQuery,
	SearchAccountsQueryVariables,
	DistinctAccountIndustriesQuery,
	DistinctAccountTypesQuery,
} from "../../../../api/graphql-operations-types";

export type AccountSearchResult = NonNullable<SearchAccountsQuery["uiapi"]["query"]["Account"]>;

export type AccountSearchOptions = ObjectSearchOptions<
	SearchAccountsQueryVariables["where"],
	SearchAccountsQueryVariables["orderBy"]
>;

export type { PicklistOption };

export async function searchAccounts(
	options: AccountSearchOptions = {},
): Promise<AccountSearchResult> {
	return searchObjects<AccountSearchResult, SearchAccountsQuery, SearchAccountsQueryVariables>(
		SEARCH_ACCOUNTS_QUERY,
		"Account",
		options,
	);
}

export async function fetchDistinctIndustries(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctAccountIndustriesQuery>(
		DISTINCT_INDUSTRIES_QUERY,
		"Account",
		"Industry",
	);
}

export async function fetchDistinctTypes(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctAccountTypesQuery>(DISTINCT_TYPES_QUERY, "Account", "Type");
}
