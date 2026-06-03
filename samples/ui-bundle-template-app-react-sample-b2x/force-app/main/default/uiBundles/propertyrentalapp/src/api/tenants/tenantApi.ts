import TENANT_PROPERTIES_QUERY from "../query/tenantProperties.graphql?raw";
import type {
	TenantPropertiesQuery,
	TenantPropertiesQueryVariables,
} from "../graphql-operations-types.js";
import { executeGraphQL } from "@/api/graphqlClient.js";

export type TenantProperty = NonNullable<
	NonNullable<
		NonNullable<NonNullable<TenantPropertiesQuery["uiapi"]["query"]["Tenant__c"]>["edges"]>[number]
	>["node"]
> & { Property__c: { value: string } };

export async function getTenantProperties(userId: string): Promise<TenantProperty[]> {
	if (!userId.trim()) return [];
	const response = await executeGraphQL<TenantPropertiesQuery, TenantPropertiesQueryVariables>(
		TENANT_PROPERTIES_QUERY,
		{ userId },
	);
	return (response.uiapi?.query?.Tenant__c?.edges ?? [])
		.map((edge) => edge?.node)
		.filter((node): node is TenantProperty => Boolean(node?.Property__c?.value));
}
