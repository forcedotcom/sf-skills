import GET_APPLICATIONS from "./query/getApplications.graphql?raw";
import UPDATE_APPLICATION_STATUS from "./query/updateApplicationStatus.graphql?raw";
import type {
	GetApplicationsQuery,
	UpdateApplicationStatusMutationVariables,
	UpdateApplicationStatusMutation,
	GetApplicationsQueryVariables,
} from "../graphql-operations-types.js";
import { executeGraphQL } from "../graphqlClient.js";

export type ApplicationNode = NonNullable<
	NonNullable<
		NonNullable<GetApplicationsQuery["uiapi"]["query"]["Application__c"]>["edges"]
	>[number]
>["node"];

export async function getApplications(): Promise<NonNullable<ApplicationNode>[]> {
	try {
		const data = await executeGraphQL<GetApplicationsQuery, GetApplicationsQueryVariables>(
			GET_APPLICATIONS,
			{},
		);
		const edges = data?.uiapi?.query?.Application__c?.edges || [];
		return edges
			.map((edge) => edge?.node)
			.filter((node): node is NonNullable<ApplicationNode> => node != null);
	} catch (error) {
		console.error("Error fetching applications:", error);
		return [];
	}
}

export async function updateApplicationStatus(
	applicationId: string,
	status: string,
): Promise<boolean> {
	const variables: UpdateApplicationStatusMutationVariables = {
		input: {
			Id: applicationId,
			Application__c: {
				Status__c: status,
			},
		},
	};
	try {
		const data = await executeGraphQL<
			UpdateApplicationStatusMutation,
			UpdateApplicationStatusMutationVariables
		>(UPDATE_APPLICATION_STATUS, variables);
		return !!data?.uiapi?.Application__cUpdate?.success;
	} catch (error) {
		console.error("Error updating application status:", error);
		return false;
	}
}
