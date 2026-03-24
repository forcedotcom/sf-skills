import GET_DASHBOARD_METRICS from "./query/getDashboardMetrics.graphql?raw";
import GET_OPEN_APPLICATIONS from "./query/getOpenApplications.graphql?raw";
import GET_USER_INFO from "./query/getUserInfo.graphql?raw";
import type {
	GetDashboardMetricsQuery,
	GetDashboardMetricsQueryVariables,
	GetOpenApplicationsQuery,
	GetOpenApplicationsQueryVariables,
	GetUserInfoQuery,
	GetUserInfoQueryVariables,
} from "../graphql-operations-types";
import { executeGraphQL } from "../graphqlClient.js";

export interface DashboardMetrics {
	totalProperties: number;
	unitsAvailable: number;
	occupiedUnits: number;
	topMaintenanceIssue: string;
	topMaintenanceIssueCount: number;
}

export type DashboardPropertyNode = NonNullable<
	NonNullable<
		NonNullable<GetDashboardMetricsQuery["uiapi"]["query"]["allProperties"]>["edges"]
	>[number]
>["node"];

export type DashboardMaintenanceNode = NonNullable<
	NonNullable<
		NonNullable<GetDashboardMetricsQuery["uiapi"]["query"]["maintenanceRequests"]>["edges"]
	>[number]
>["node"];

export type OpenApplicationNode = NonNullable<
	NonNullable<
		NonNullable<GetOpenApplicationsQuery["uiapi"]["query"]["Application__c"]>["edges"]
	>[number]
>["node"];

export async function getDashboardMetrics(): Promise<{
	properties: NonNullable<DashboardPropertyNode>[];
	maintenanceRequests: NonNullable<DashboardMaintenanceNode>[];
}> {
	const response = await executeGraphQL<
		GetDashboardMetricsQuery,
		GetDashboardMetricsQueryVariables
	>(GET_DASHBOARD_METRICS, {});
	const properties =
		response?.uiapi?.query?.allProperties?.edges
			?.map((edge) => edge?.node)
			.filter((node): node is NonNullable<DashboardPropertyNode> => node != null) || [];
	const maintenanceRequests =
		response?.uiapi?.query?.maintenanceRequests?.edges
			?.map((edge) => edge?.node)
			.filter((node): node is NonNullable<DashboardMaintenanceNode> => node != null) || [];
	return { properties, maintenanceRequests };
}

export async function getOpenApplications(
	first: number = 5,
): Promise<NonNullable<OpenApplicationNode>[]> {
	const variables: GetOpenApplicationsQueryVariables = { first };
	const data = await executeGraphQL<GetOpenApplicationsQuery, GetOpenApplicationsQueryVariables>(
		GET_OPEN_APPLICATIONS,
		variables,
	);
	return (
		data?.uiapi?.query?.Application__c?.edges
			?.map((edge) => edge?.node)
			.filter((node): node is NonNullable<OpenApplicationNode> => node != null) || []
	);
}

export async function getUserInfo(): Promise<{ name: string; id: string } | null> {
	try {
		const data = await executeGraphQL<GetUserInfoQuery, GetUserInfoQueryVariables>(
			GET_USER_INFO,
			{},
		);
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

export const calculateMetrics = (
	properties: NonNullable<DashboardPropertyNode>[],
): DashboardMetrics => {
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
