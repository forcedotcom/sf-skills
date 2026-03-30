import SEARCH_QUERY from "./query/searchApplications.graphql?raw";
import DISTINCT_STATUS_QUERY from "./query/distinctApplicationStatus.graphql?raw";
import {
	searchObjects,
	fetchDistinctValues,
	type ObjectSearchOptions,
	type PicklistOption,
} from "../../features/object-search/api/objectSearchService";
import type {
	SearchApplicationsQuery,
	SearchApplicationsQueryVariables,
	DistinctApplicationStatusQuery,
} from "../graphql-operations-types";

export type ApplicationSearchResult = NonNullable<
	SearchApplicationsQuery["uiapi"]["query"]["Application__c"]
>;

export type ApplicationSearchNode = NonNullable<
	NonNullable<NonNullable<ApplicationSearchResult["edges"]>[number]>["node"]
>;

export type ApplicationSearchOptions = ObjectSearchOptions<
	SearchApplicationsQueryVariables["where"],
	SearchApplicationsQueryVariables["orderBy"]
>;

export type { PicklistOption };

export async function searchApplications(
	options: ApplicationSearchOptions = {},
): Promise<ApplicationSearchResult> {
	return searchObjects<
		ApplicationSearchResult,
		SearchApplicationsQuery,
		SearchApplicationsQueryVariables
	>(SEARCH_QUERY, "Application__c", options);
}

export async function fetchDistinctApplicationStatus(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctApplicationStatusQuery>(
		DISTINCT_STATUS_QUERY,
		"Application__c",
		"Status__c",
	);
}
