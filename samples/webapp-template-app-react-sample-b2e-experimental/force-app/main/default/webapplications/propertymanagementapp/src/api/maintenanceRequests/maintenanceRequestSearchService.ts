import SEARCH_QUERY from "./query/searchMaintenanceRequests.graphql?raw";
import DISTINCT_STATUS_QUERY from "./query/distinctMaintenanceRequestStatus.graphql?raw";
import DISTINCT_TYPE_QUERY from "./query/distinctMaintenanceRequestType.graphql?raw";
import DISTINCT_PRIORITY_QUERY from "./query/distinctMaintenanceRequestPriority.graphql?raw";
import {
	searchObjects,
	fetchDistinctValues,
	type ObjectSearchOptions,
	type PicklistOption,
} from "../../features/object-search/api/objectSearchService";
import type {
	SearchMaintenanceRequestsQuery,
	SearchMaintenanceRequestsQueryVariables,
	DistinctMaintenanceRequestStatusQuery,
	DistinctMaintenanceRequestTypeQuery,
	DistinctMaintenanceRequestPriorityQuery,
} from "../graphql-operations-types";

export type MaintenanceRequestSearchResult = NonNullable<
	SearchMaintenanceRequestsQuery["uiapi"]["query"]["Maintenance_Request__c"]
>;

export type MaintenanceRequestSearchNode = NonNullable<
	NonNullable<NonNullable<MaintenanceRequestSearchResult["edges"]>[number]>["node"]
>;

export type MaintenanceRequestSearchOptions = ObjectSearchOptions<
	SearchMaintenanceRequestsQueryVariables["where"],
	SearchMaintenanceRequestsQueryVariables["orderBy"]
>;

export type { PicklistOption };

export async function searchMaintenanceRequests(
	options: MaintenanceRequestSearchOptions = {},
): Promise<MaintenanceRequestSearchResult> {
	return searchObjects<
		MaintenanceRequestSearchResult,
		SearchMaintenanceRequestsQuery,
		SearchMaintenanceRequestsQueryVariables
	>(SEARCH_QUERY, "Maintenance_Request__c", options);
}

export async function fetchDistinctMaintenanceRequestStatus(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctMaintenanceRequestStatusQuery>(
		DISTINCT_STATUS_QUERY,
		"Maintenance_Request__c",
		"Status__c",
	);
}

export async function fetchDistinctMaintenanceRequestType(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctMaintenanceRequestTypeQuery>(
		DISTINCT_TYPE_QUERY,
		"Maintenance_Request__c",
		"Type__c",
	);
}

export async function fetchDistinctMaintenanceRequestPriority(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctMaintenanceRequestPriorityQuery>(
		DISTINCT_PRIORITY_QUERY,
		"Maintenance_Request__c",
		"Priority__c",
	);
}
