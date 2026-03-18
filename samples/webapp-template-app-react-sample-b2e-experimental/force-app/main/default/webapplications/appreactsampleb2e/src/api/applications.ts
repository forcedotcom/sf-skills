import { gql } from "@salesforce/sdk-data";
import type { Application } from "../lib/types.js";
import type {
	GetApplicationsQuery,
	UpdateApplicationStatusMutationVariables,
	UpdateApplicationStatusMutation,
} from "./graphql-operations-types.js";
import { executeGraphQL } from "./graphqlClient.js";

// Query to get all applications
const GET_APPLICATIONS = gql`
	query GetApplications {
		uiapi {
			query {
				Application__c(orderBy: { Start_Date__c: { order: DESC } }) {
					edges {
						node {
							Id
							Name {
								value
							}
							User__r {
								FirstName {
									value
								}
								LastName {
									value
								}
							}
							Property__r {
								Name {
									value
								}
								Address__c {
									value
								}
							}
							Start_Date__c {
								value
							}
							Status__c {
								value
							}
							Employment__c {
								value
							}
							References__c {
								value
							}
						}
					}
				}
			}
		}
	}
`;

// Mutation to update application status
const UPDATE_APPLICATION_STATUS = gql`
	mutation UpdateApplicationStatus($input: Application__cUpdateInput!) {
		uiapi {
			Application__cUpdate(input: $input) {
				Record {
					Id
					Status__c {
						value
					}
				}
				success
			}
		}
	}
`;

export async function getApplications(): Promise<Application[]> {
	try {
		const data = await executeGraphQL<GetApplicationsQuery>(GET_APPLICATIONS);
		const edges = data?.uiapi?.query?.Application__c?.edges || [];

		return edges
			.map((edge) => {
				if (!edge || !edge.node) return null;
				const node = edge.node;
				const firstName = node.User__r?.FirstName?.value || "";
				const lastName = node.User__r?.LastName?.value || "";
				const applicantName = `${firstName} ${lastName}`.trim() || "Unknown";

				return {
					id: node.Id,
					applicantName,
					propertyAddress: node.Property__r?.Address__c?.value || "Unknown Property",
					propertyName: node.Property__r?.Name?.value || "",
					submittedDate: node.Start_Date__c?.value || "",
					startDate: node.Start_Date__c?.value || "",
					status: node.Status__c?.value || "Unknown",
					employment: node.Employment__c?.value || "",
					references: node.References__c?.value || "",
				};
			})
			.filter((app) => app !== null) as Application[];
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
