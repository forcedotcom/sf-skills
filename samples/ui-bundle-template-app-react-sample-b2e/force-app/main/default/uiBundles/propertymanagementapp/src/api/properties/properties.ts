import GET_PROPERTIES_PAGINATED from "./query/getProperties.graphql?raw";
import type {
	GetPropertiesQueryVariables,
	GetPropertiesQuery,
} from "../graphql-operations-types.js";
import { executeGraphQL } from "../graphqlClient.js";

export type PropertyNode = NonNullable<
	NonNullable<NonNullable<GetPropertiesQuery["uiapi"]["query"]["Property__c"]>["edges"]>[number]
>["node"];

export interface PropertiesResult {
	properties: NonNullable<PropertyNode>[];
	pageInfo: {
		hasNextPage: boolean;
		endCursor?: string | null;
	};
}

export async function getProperties(first: number = 12, after?: string): Promise<PropertiesResult> {
	const variables: GetPropertiesQueryVariables = { first };
	if (after) {
		variables.after = after;
	}
	const response = await executeGraphQL<GetPropertiesQuery, GetPropertiesQueryVariables>(
		GET_PROPERTIES_PAGINATED,
		variables,
	);
	const edges = response?.uiapi?.query?.Property__c?.edges || [];
	const pageInfo = response?.uiapi?.query?.Property__c?.pageInfo || {
		hasNextPage: false,
		endCursor: null,
	};

	const properties = edges
		.map((edge) => edge?.node)
		.filter((node): node is NonNullable<PropertyNode> => node != null);

	return {
		properties,
		pageInfo,
	};
}
