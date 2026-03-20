import { gql } from "@salesforce/sdk-data";
import type { DashboardMetrics, Application } from "../lib/types.js";
import type {
	GetDashboardMetricsQuery,
	GetOpenApplicationsQuery,
	GetOpenApplicationsQueryVariables,
	GetUserInfoQuery,
} from "./graphql-operations-types.js";
import { executeGraphQL } from "./graphqlClient.js";

// Query to get property counts for dashboard metrics
const GET_DASHBOARD_METRICS = gql`
	query GetDashboardMetrics {
		uiapi {
			query {
				allProperties: Property__c {
					edges {
						node {
							Id
							Status__c {
								value
							}
						}
					}
				}
				maintenanceRequests: Maintenance_Request__c(first: 100) {
					edges {
						node {
							Id
							Type__c {
								value
							}
						}
					}
				}
			}
		}
	}
`;

// Query to get open applications
const GET_OPEN_APPLICATIONS = gql`
	query GetOpenApplications($first: Int) {
		uiapi {
			query {
				Application__c(
					first: $first
					where: { Status__c: { in: ["Submitted", "Background Check"] } }
					orderBy: { CreatedDate: { order: ASC } }
				) {
					edges {
						node {
							Id
							Name {
								value
							}
							User__r {
								Name {
									value
								}
							}
							Property__r {
								Address__c {
									value
								}
							}
							Status__c {
								value
							}
							CreatedDate {
								value
							}
						}
					}
				}
			}
		}
	}
`;

// Query to get current user information
const GET_USER_INFO = gql`
	query GetUserInfo {
		uiapi {
			query {
				User(first: 1) {
					edges {
						node {
							Id
							Name {
								value
							}
						}
					}
				}
			}
		}
	}
`;

// Fetch dashboard metrics
export async function getDashboardMetrics(): Promise<{
	properties: unknown[];
	maintenanceRequests: unknown[];
}> {
	const response = await executeGraphQL<GetDashboardMetricsQuery>(GET_DASHBOARD_METRICS);
	const properties = response?.uiapi?.query?.allProperties?.edges?.map((edge) => edge?.node) || [];
	const maintenanceRequests =
		response?.uiapi?.query?.maintenanceRequests?.edges?.map((edge) => edge?.node) || [];
	return { properties, maintenanceRequests };
}

// Fetch open applications
export async function getOpenApplications(first: number = 5): Promise<Application[]> {
	const variables: GetOpenApplicationsQueryVariables = { first };
	const data = await executeGraphQL<GetOpenApplicationsQuery, GetOpenApplicationsQueryVariables>(
		GET_OPEN_APPLICATIONS,
		variables,
	);
	const apps =
		data?.uiapi?.query?.Application__c?.edges?.map((edge) => transformApplication(edge?.node)) ||
		[];
	return apps;
}

// Fetch current user information
export async function getUserInfo(): Promise<{ name: string; id: string } | null> {
	try {
		const data = await executeGraphQL<GetUserInfoQuery>(GET_USER_INFO);
		const user = data?.uiapi?.query?.User?.edges?.[0]?.node;
		if (user) {
			return {
				id: user.Id,
				name: user.Name?.value || "User",
			};
		}
		return null;
	} catch (error) {
		console.error("Error fetching user info:", error);
		return null;
	}
}

// Helper function to calculate dashboard metrics from properties
export const calculateMetrics = (properties: any[]): DashboardMetrics => {
	const total = properties.length;
	const available = properties.filter((p) => p.Status__c?.value === "Available").length;
	const occupied = properties.filter((p) => p.Status__c?.value === "Rented").length;

	return {
		totalProperties: total,
		unitsAvailable: available,
		occupiedUnits: occupied,
		topMaintenanceIssue: "Plumbing",
		topMaintenanceIssueCount: 0,
	};
};

// Helper function to transform application data
function transformApplication(node: any): Application {
	const createdDate = new Date(node.CreatedDate?.value);
	const daysAgo = Math.floor((Date.now() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
	const timeAgo = daysAgo === 0 ? "today" : daysAgo === 1 ? "1 day ago" : `${daysAgo} days ago`;

	return {
		id: node.Id,
		applicantName: node.User__r?.Name?.value || "Unknown",
		propertyAddress: node.Property__r?.Address__c?.value || "Unknown Address",
		submittedDate: timeAgo,
		status: node.Status__c?.value?.toLowerCase() || "pending",
	};
}
