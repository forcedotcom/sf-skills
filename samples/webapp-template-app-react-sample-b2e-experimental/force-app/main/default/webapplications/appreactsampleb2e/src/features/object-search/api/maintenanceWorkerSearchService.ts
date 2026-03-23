import SEARCH_QUERY from "./query/searchMaintenanceWorkers.graphql?raw";
import DISTINCT_TYPE_QUERY from "./query/distinctMaintenanceWorkerEmploymentType.graphql?raw";
import {
	searchObjects,
	fetchDistinctValues,
	type ObjectSearchOptions,
	type PicklistOption,
} from "./objectSearchService";
import type {
	SearchMaintenanceWorkersQuery,
	SearchMaintenanceWorkersQueryVariables,
	DistinctMaintenanceWorkerEmploymentTypeQuery,
} from "../../../api/graphql-operations-types.js";

export type MaintenanceWorkerSearchResult = NonNullable<
	SearchMaintenanceWorkersQuery["uiapi"]["query"]["Maintenance_Worker__c"]
>;

export type MaintenanceWorkerSearchOptions = ObjectSearchOptions<
	SearchMaintenanceWorkersQueryVariables["where"],
	SearchMaintenanceWorkersQueryVariables["orderBy"]
>;

export type { PicklistOption };

export async function searchMaintenanceWorkers(
	options: MaintenanceWorkerSearchOptions = {},
): Promise<MaintenanceWorkerSearchResult> {
	return searchObjects<
		MaintenanceWorkerSearchResult,
		SearchMaintenanceWorkersQuery,
		SearchMaintenanceWorkersQueryVariables
	>(SEARCH_QUERY, "Maintenance_Worker__c", options);
}

export async function fetchDistinctMaintenanceWorkerType(): Promise<PicklistOption[]> {
	return fetchDistinctValues<DistinctMaintenanceWorkerEmploymentTypeQuery>(
		DISTINCT_TYPE_QUERY,
		"Maintenance_Worker__c",
		"Employment_Type__c",
	);
}
