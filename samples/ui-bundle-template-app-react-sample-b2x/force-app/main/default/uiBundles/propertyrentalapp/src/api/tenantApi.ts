import TENANT_ACCESS_QUERY from "./query/tenantAccess.graphql?raw";
import type { TenantAccessQuery, TenantAccessQueryVariables } from "./graphql-operations-types.js";
import { executeGraphQL } from "@/api/graphqlClient.js";

export async function hasTenantAccess(userId: string): Promise<boolean> {
	if (!userId.trim()) return false;
	const response = await executeGraphQL<TenantAccessQuery, TenantAccessQueryVariables>(
		TENANT_ACCESS_QUERY,
		{ userId },
	);
	return Boolean(response.uiapi?.query?.Tenant__c?.edges?.[0]?.node?.Id);
}
