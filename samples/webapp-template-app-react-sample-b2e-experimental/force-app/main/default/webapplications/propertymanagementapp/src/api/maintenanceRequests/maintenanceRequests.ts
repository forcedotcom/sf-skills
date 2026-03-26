import GET_MAINTENANCE_REQUESTS from "./query/getMaintenanceRequests.graphql?raw";
import GET_ALL_MAINTENANCE_REQUESTS from "./query/getAllMaintenanceRequests.graphql?raw";
import UPDATE_MAINTENANCE_STATUS from "./query/updateMaintenanceStatus.graphql?raw";
import type {
	GetMaintenanceRequestsQuery,
	GetMaintenanceRequestsQueryVariables,
	GetAllMaintenanceRequestsQuery,
	GetAllMaintenanceRequestsQueryVariables,
	UpdateMaintenanceStatusMutation,
	UpdateMaintenanceStatusMutationVariables,
} from "../graphql-operations-types.js";
import { executeGraphQL } from "../graphqlClient.js";

export type MaintenanceRequestNode = NonNullable<
	NonNullable<
		NonNullable<GetMaintenanceRequestsQuery["uiapi"]["query"]["Maintenance_Request__c"]>["edges"]
	>[number]
>["node"];

export type AllMaintenanceRequestNode = NonNullable<
	NonNullable<
		NonNullable<GetAllMaintenanceRequestsQuery["uiapi"]["query"]["Maintenance_Request__c"]>["edges"]
	>[number]
>["node"];

export async function getMaintenanceRequests(
	first: number = 5,
): Promise<NonNullable<MaintenanceRequestNode>[]> {
	const variables: GetMaintenanceRequestsQueryVariables = { first };
	const data = await executeGraphQL<
		GetMaintenanceRequestsQuery,
		GetMaintenanceRequestsQueryVariables
	>(GET_MAINTENANCE_REQUESTS, variables);
	return (
		data?.uiapi?.query?.Maintenance_Request__c?.edges
			?.map((edge) => edge?.node)
			.filter((node): node is NonNullable<MaintenanceRequestNode> => node != null) || []
	);
}

export async function getAllMaintenanceRequests(
	first: number = 100,
): Promise<NonNullable<AllMaintenanceRequestNode>[]> {
	const variables: GetAllMaintenanceRequestsQueryVariables = { first };
	const data = await executeGraphQL<
		GetAllMaintenanceRequestsQuery,
		GetAllMaintenanceRequestsQueryVariables
	>(GET_ALL_MAINTENANCE_REQUESTS, variables);
	return (
		data?.uiapi?.query?.Maintenance_Request__c?.edges
			?.map((edge) => edge?.node)
			.filter((node): node is NonNullable<AllMaintenanceRequestNode> => node != null) || []
	);
}

export async function updateMaintenanceStatus(requestId: string, status: string): Promise<boolean> {
	const variables: UpdateMaintenanceStatusMutationVariables = {
		input: {
			Id: requestId,
			Maintenance_Request__c: {
				Status__c: status,
			},
		},
	};
	try {
		const data = await executeGraphQL<
			UpdateMaintenanceStatusMutation,
			UpdateMaintenanceStatusMutationVariables
		>(UPDATE_MAINTENANCE_STATUS, variables);
		return !!data?.uiapi?.Maintenance_Request__cUpdate?.success;
	} catch (error) {
		console.error("Error updating maintenance status:", error);
		return false;
	}
}
