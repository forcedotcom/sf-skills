import GET_APPLICATIONS from "./query/getApplications.graphql?raw";
import UPDATE_APPLICATION_STATUS from "./query/updateApplicationStatus.graphql?raw";
import APPLICATION_FOR_APPROVAL_QUERY from "./query/applicationForApproval.graphql?raw";
import USER_BY_CONTACT_QUERY from "./query/userByContact.graphql?raw";
import EXISTING_TENANT_QUERY from "./query/existingTenant.graphql?raw";
import { createRecord } from "@salesforce/ui-bundle/api";
import type {
	GetApplicationsQuery,
	GetApplicationsQueryVariables,
	UpdateApplicationStatusMutation,
	UpdateApplicationStatusMutationVariables,
	ApplicationForApprovalQuery,
	ApplicationForApprovalQueryVariables,
	UserByContactQuery,
	UserByContactQueryVariables,
	ExistingTenantQuery,
	ExistingTenantQueryVariables,
} from "../graphql-operations-types.js";
import { executeGraphQL } from "../graphqlClient.js";

export type ApplicationNode = NonNullable<
	NonNullable<
		NonNullable<GetApplicationsQuery["uiapi"]["query"]["Application__c"]>["edges"]
	>[number]
>["node"];

const TENANT_OBJECT_API_NAME = "Tenant__c";

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
	const normalizedStatus = status.trim().toLowerCase();
	if (normalizedStatus === "approved") {
		await ensureTenantForApprovedApplication(applicationId);
	}

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

async function ensureTenantForApprovedApplication(applicationId: string): Promise<void> {
	const appData = await executeGraphQL<
		ApplicationForApprovalQuery,
		ApplicationForApprovalQueryVariables
	>(APPLICATION_FOR_APPROVAL_QUERY, { applicationId });
	const applicationNode = appData.uiapi?.query?.Application__c?.edges?.[0]?.node;
	if (!applicationNode) {
		throw new Error("Application record not found.");
	}

	const contactId = applicationNode.User__c?.value ?? null;
	const propertyId = applicationNode.Property__c?.value ?? null;
	const startDate = applicationNode.Start_Date__c?.value ?? null;

	if (!contactId || !propertyId) {
		return;
	}

	const userData = await executeGraphQL<UserByContactQuery, UserByContactQueryVariables>(
		USER_BY_CONTACT_QUERY,
		{ contactId },
	);
	const userId = userData.uiapi?.query?.User?.edges?.[0]?.node?.Id ?? null;
	if (!userId) {
		return;
	}

	const existingTenantData = await executeGraphQL<
		ExistingTenantQuery,
		ExistingTenantQueryVariables
	>(EXISTING_TENANT_QUERY, {
		userId,
		propertyId,
	});
	const existingTenantId = existingTenantData.uiapi?.query?.Tenant__c?.edges?.[0]?.node?.Id ?? null;
	if (existingTenantId) return;

	const tenantFields: Record<string, unknown> = {
		User__c: userId,
		Property__c: propertyId,
		User_Status__c: "Tenant",
		Status__c: "Active",
	};
	if (startDate) {
		tenantFields.Start_Date__c = String(startDate);
	}

	await createRecord(TENANT_OBJECT_API_NAME, tenantFields);
}
