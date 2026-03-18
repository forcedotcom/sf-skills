import { gql } from "@salesforce/sdk-data";
import type { Property } from "../lib/types.js";
import type {
	GetPropertiesQueryVariables,
	GetPropertiesQuery,
} from "./graphql-operations-types.js";
import { executeGraphQL } from "./graphqlClient.js";

// GraphQL query to get properties with pagination
const GET_PROPERTIES_PAGINATED = gql`
	query GetProperties($first: Int, $after: String) {
		uiapi {
			query {
				Property__c(first: $first, after: $after, orderBy: { CreatedDate: { order: DESC } }) {
					edges {
						node {
							Id
							Name {
								value
							}
							Address__c {
								value
							}
							Description__c {
								value
							}
							Type__c {
								value
							}
							Status__c {
								value
							}
							Monthly_Rent__c {
								value
							}
							Bedrooms__c {
								value
							}
							Bathrooms__c {
								value
							}
							Sq_Ft__c {
								value
							}
							Year_Built__c {
								value
							}
							Hero_Image__c {
								value
							}
							Deposit__c {
								value
							}
							Parking__c {
								value
							}
							Pet_Friendly__c {
								value
							}
							Available_Date__c {
								value
							}
							Lease_Term__c {
								value
							}
							Features__c {
								value
							}
							Utilities__c {
								value
							}
							Tour_URL__c {
								value
							}
							CreatedDate {
								value
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

export interface PropertiesResult {
	properties: Property[];
	pageInfo: {
		hasNextPage: boolean;
		endCursor?: string | null;
	};
}

// Fetch properties with pagination
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

	const properties = edges.map((edge) => transformProperty(edge?.node));

	return {
		properties,
		pageInfo,
	};
}

// Helper function to transform property data from GraphQL to Property type
function transformProperty(node: any): Property {
	// Extract year from CreatedDate for "Since [year]" display
	const createdYear = node.CreatedDate?.value
		? new Date(node.CreatedDate.value).getFullYear().toString()
		: undefined;

	// Parse multi-picklist values (comma-separated strings to arrays)
	const features = node.Features__c?.value ? node.Features__c.value.split(";") : undefined;
	const utilities = node.Utilities__c?.value ? node.Utilities__c.value.split(";") : undefined;

	return {
		id: node.Id,
		name: node.Name?.value || "Unnamed Property",
		address: node.Address__c?.value || "Address not available",
		type:
			(node.Type__c?.value?.toLowerCase() as "apartment" | "house" | "commercial") || "apartment",
		status:
			(node.Status__c?.value?.toLowerCase() as "available" | "rented" | "maintenance") ||
			"available",
		monthlyRent: node.Monthly_Rent__c?.value || 0,
		bedrooms: node.Bedrooms__c?.value,
		bathrooms: node.Bathrooms__c?.value,
		heroImage: node.Hero_Image__c?.value,
		description: node.Description__c?.value,
		sqFt: node.Sq_Ft__c?.value,
		yearBuilt: node.Year_Built__c?.value,
		deposit: node.Deposit__c?.value,
		parking: node.Parking__c?.value,
		petFriendly: node.Pet_Friendly__c?.value,
		availableDate: node.Available_Date__c?.value,
		leaseTerm: node.Lease_Term__c?.value,
		features,
		utilities,
		tourUrl: node.Tour_URL__c?.value,
		createdDate: createdYear,
	};
}
