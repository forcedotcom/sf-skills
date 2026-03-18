import { gql } from "@salesforce/sdk-data";
import type { MaintenanceRequest } from "../lib/types.js";
import type {
	GetMaintenanceRequestsQuery,
	GetMaintenanceRequestsQueryVariables,
	GetAllMaintenanceRequestsQuery,
	GetAllMaintenanceRequestsQueryVariables,
	UpdateMaintenanceStatusMutation,
	UpdateMaintenanceStatusMutationVariables,
} from "./graphql-operations-types.js";
import { executeGraphQL } from "./graphqlClient.js";

// Query to get recent maintenance requests
const GET_MAINTENANCE_REQUESTS = gql`
	query GetMaintenanceRequests($first: Int) {
		uiapi {
			query {
				Maintenance_Request__c(first: $first, orderBy: { Priority__c: { order: DESC } }) {
					edges {
						node {
							Id
							Name {
								value
							}
							Property__r {
								Address__c {
									value
								}
							}
							User__r {
								Name {
									value
								}
							}
							Type__c {
								value
							}
							Priority__c {
								value
							}
							Status__c {
								value
							}
							Description__c {
								value
							}
							Scheduled__c {
								value
							}
						}
					}
				}
			}
		}
	}
`;

// Query to get all maintenance requests for the maintenance page
const GET_ALL_MAINTENANCE_REQUESTS = gql`
	query GetAllMaintenanceRequests($first: Int, $after: String) {
		uiapi {
			query {
				Maintenance_Request__c(
					first: $first
					after: $after
					orderBy: { Priority__c: { order: DESC }, Scheduled__c: { order: ASC } }
				) {
					edges {
						node {
							Id
							Name {
								value
							}
							Description__c {
								value
							}
							Type__c {
								value
							}
							Priority__c {
								value
							}
							Status__c {
								value
							}
							Scheduled__c {
								value
							}
							Property__r {
								Address__c {
									value
								}
								Name {
									value
								}
							}
							User__r {
								Name {
									value
								}
							}
							Assigned_Worker__r {
								Name {
									value
								}
								Employment_Type__c {
									value
								}
							}
							ContentDocumentLinks(first: 1) {
								edges {
									node {
										ContentDocument {
											LatestPublishedVersionId {
												value
											}
										}
									}
								}
							}
						}
					}
					pageInfo {
						hasNextPage
						endCursor
					}
				}
			}
		}
	}
`;

// Mutation to update maintenance request status
const UPDATE_MAINTENANCE_STATUS = gql`
	mutation UpdateMaintenanceStatus($input: Maintenance_Request__cUpdateInput!) {
		uiapi {
			Maintenance_Request__cUpdate(input: $input) {
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

// Fetch maintenance requests for dashboard
export async function getMaintenanceRequests(first: number = 5): Promise<MaintenanceRequest[]> {
	const variables: GetMaintenanceRequestsQueryVariables = { first };
	const data = await executeGraphQL<
		GetMaintenanceRequestsQuery,
		GetMaintenanceRequestsQueryVariables
	>(GET_MAINTENANCE_REQUESTS, variables);
	const requests =
		data?.uiapi?.query?.Maintenance_Request__c?.edges?.map((edge) =>
			transformMaintenanceRequest(edge?.node),
		) || [];
	return requests;
}

// Fetch all maintenance requests for the maintenance page
export async function getAllMaintenanceRequests(
	first: number = 100,
): Promise<MaintenanceRequest[]> {
	const variables: GetAllMaintenanceRequestsQueryVariables = { first };
	const data = await executeGraphQL<
		GetAllMaintenanceRequestsQuery,
		GetAllMaintenanceRequestsQueryVariables
	>(GET_ALL_MAINTENANCE_REQUESTS, variables);
	const requests =
		data?.uiapi?.query?.Maintenance_Request__c?.edges?.map((edge) =>
			transformMaintenanceTaskFull(edge?.node),
		) || [];
	return requests;
}

// Helper function to map priority values to badge format
function mapPriority(
	priority: string | undefined,
): "Emergency (2hr)" | "High (Same Day)" | "Standard" {
	if (!priority) return "Standard";
	const priorityLower = priority.toLowerCase();
	if (priorityLower.includes("emergency")) return "Emergency (2hr)";
	if (priorityLower.includes("high")) return "High (Same Day)";
	return "Standard";
}

// Helper function to transform maintenance request data
function transformMaintenanceRequest(node: any): MaintenanceRequest {
	const scheduledDate = node.Scheduled__c?.value
		? new Date(node.Scheduled__c.value).toLocaleString()
		: undefined;

	return {
		id: node.Id,
		propertyAddress: node.Property__r?.Address__c?.value || "Unknown Address",
		issueType: node.Type__c?.value || "General",
		priority: mapPriority(node.Priority__c?.value),
		status: node.Status__c?.value || "New",
		assignedWorker: undefined,
		scheduledDateTime: scheduledDate,
		description: node.Description__c?.value || "",
		tenantName: node.User__r?.Name?.value || "Unknown",
	};
}

// Helper function to transform maintenance request data with all fields for maintenance page
function transformMaintenanceTaskFull(node: any): MaintenanceRequest {
	const scheduledDate = node.Scheduled__c?.value ? new Date(node.Scheduled__c.value) : null;
	const formattedDate = scheduledDate
		? scheduledDate.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
			", " +
			scheduledDate.toLocaleTimeString("en-US", {
				hour: "numeric",
				minute: "2-digit",
				hour12: true,
			})
		: undefined;

	// Get image URL from ContentDocumentLinks
	const imageVersionId =
		node.ContentDocumentLinks?.edges?.[0]?.node?.ContentDocument?.LatestPublishedVersionId?.value;
	const imageUrl = imageVersionId
		? `/sfc/servlet.shepherd/version/download/${imageVersionId}`
		: undefined;

	// Get tenant unit from Property
	const tenantUnit = node.Property__r?.Name?.value || node.Property__r?.Address__c?.value;

	// Get assigned worker name and employment type from Assigned_Worker__r
	const assignedWorkerName = node.Assigned_Worker__r?.Name?.value;
	const assignedWorkerOrg = node.Assigned_Worker__r?.Employment_Type__c?.value;

	return {
		id: node.Id,
		propertyAddress: node.Property__r?.Address__c?.value || "Unknown Address",
		issueType: node.Type__c?.value || "General",
		priority: mapPriority(node.Priority__c?.value),
		status: node.Status__c?.value || "New",
		assignedWorker: assignedWorkerName,
		scheduledDateTime: scheduledDate?.toLocaleString(),
		description: node.Description__c?.value || "",
		tenantName: node.User__r?.Name?.value || "Unknown",
		imageUrl,
		tenantUnit,
		assignedWorkerName,
		assignedWorkerOrg,
		formattedDate,
	};
}

// Update maintenance request status
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
