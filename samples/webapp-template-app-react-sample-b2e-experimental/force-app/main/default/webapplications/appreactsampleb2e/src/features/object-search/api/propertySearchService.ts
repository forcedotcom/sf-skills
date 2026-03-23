import SEARCH_PROPERTIES_QUERY from "./query/searchProperties.graphql?raw";
import DISTINCT_STATUS_QUERY from "./query/distinctPropertyStatus.graphql?raw";
import DISTINCT_TYPE_QUERY from "./query/distinctPropertyType.graphql?raw";
import {
	searchObjects,
	fetchDistinctValues,
	type ObjectSearchOptions,
	type PicklistOption,
} from "./objectSearchService";
import type {
	SearchPropertiesQuery,
	SearchPropertiesQueryVariables,
	DistinctPropertyStatusQuery,
	DistinctPropertyTypeQuery,
} from "../../../api/graphql-operations-types.js";

export type PropertySearchResult = NonNullable<
	SearchPropertiesQuery["uiapi"]["query"]["Property__c"]
>;

export type PropertySearchOptions = ObjectSearchOptions<
	SearchPropertiesQueryVariables["where"],
	SearchPropertiesQueryVariables["orderBy"]
>;

export type { PicklistOption };

export async function searchProperties(
	options: PropertySearchOptions = {},
): Promise<PropertySearchResult> {
	return searchObjects<PropertySearchResult, SearchPropertiesQuery, SearchPropertiesQueryVariables>(
		SEARCH_PROPERTIES_QUERY,
		"Property__c",
		options,
	);
}

export async function fetchDistinctPropertyStatus(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctPropertyStatusQuery>(
		DISTINCT_STATUS_QUERY,
		"Property__c",
		"Status__c",
	);
}

export async function fetchDistinctPropertyType(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctPropertyTypeQuery>(
		DISTINCT_TYPE_QUERY,
		"Property__c",
		"Type__c",
	);
}
