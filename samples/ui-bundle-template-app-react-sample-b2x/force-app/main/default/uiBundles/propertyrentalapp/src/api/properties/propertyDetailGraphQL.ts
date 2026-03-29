/**
 * GraphQL queries for property detail and related data.
 */
import LISTING_QUERY from "./query/listingById.graphql?raw";
import PROPERTY_DETAIL_QUERY from "./query/propertyDetailById.graphql?raw";
import PROPERTY_ADDRESSES_BY_IDS_QUERY from "./query/propertyAddressesByIds.graphql?raw";
import type {
	ListingByIdQuery,
	ListingByIdQueryVariables,
	PropertyDetailByIdQuery,
	PropertyDetailByIdQueryVariables,
	PropertyAddressesByIdsQuery,
	PropertyAddressesByIdsQueryVariables,
} from "@/api/graphql-operations-types.js";
import { executeGraphQL } from "@/api/graphqlClient.js";

// ---- Listing by Id (used by usePropertyDetail fallback for listing ID routes) ----

export type ListingDetail = NonNullable<
	NonNullable<
		NonNullable<ListingByIdQuery["uiapi"]["query"]["Property_Listing__c"]>["edges"]
	>[number]
>["node"];

export async function fetchListingById(listingId: string): Promise<ListingDetail | null> {
	const variables: ListingByIdQueryVariables = { listingId };
	const res = await executeGraphQL<ListingByIdQuery, ListingByIdQueryVariables>(
		LISTING_QUERY,
		variables,
	);
	return res.uiapi?.query?.Property_Listing__c?.edges?.[0]?.node ?? null;
}

// ---- Property Detail (single query with all relationships) ----

export type PropertyDetailNode = NonNullable<
	NonNullable<
		NonNullable<PropertyDetailByIdQuery["uiapi"]["query"]["Property__c"]>["edges"]
	>[number]
>["node"];

export async function fetchPropertyDetailById(
	propertyId: string,
): Promise<PropertyDetailNode | null> {
	const variables: PropertyDetailByIdQueryVariables = { propertyId };
	const res = await executeGraphQL<PropertyDetailByIdQuery, PropertyDetailByIdQueryVariables>(
		PROPERTY_DETAIL_QUERY,
		variables,
	);
	return res.uiapi?.query?.Property__c?.edges?.[0]?.node ?? null;
}

/** Fetch Address__c for multiple properties (for map markers). Returns id -> address. */
export async function fetchPropertyAddresses(
	propertyIds: string[],
): Promise<Record<string, string>> {
	const uniq = [...new Set(propertyIds)].filter(Boolean);
	if (uniq.length === 0) return {};

	const res = await executeGraphQL<
		PropertyAddressesByIdsQuery,
		PropertyAddressesByIdsQueryVariables
	>(PROPERTY_ADDRESSES_BY_IDS_QUERY, { propertyIds: uniq });
	const edges = res.uiapi?.query?.Property__c?.edges ?? [];
	const entries = edges.map((edge) => {
		const n = edge?.node;
		if (!n) return null;
		const address =
			n.Address__c?.value != null
				? String(n.Address__c.value)
				: (n.Address__c?.displayValue ?? null);
		return address ? ([n.Id, address] as const) : null;
	});
	return Object.fromEntries(entries.filter((e): e is readonly [string, string] => e != null));
}
