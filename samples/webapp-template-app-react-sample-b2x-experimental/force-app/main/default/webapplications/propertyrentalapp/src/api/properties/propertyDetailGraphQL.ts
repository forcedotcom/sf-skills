/**
 * GraphQL queries for Property_Listing__c detail and related Property__c data:
 * Property_Image__c, Property_Cost__c, Property_Feature__c.
 */
import { gql } from "@salesforce/sdk-data";
import type {
	ListingByIdQuery,
	ListingByIdQueryVariables,
	PropertyByIdQuery,
	PropertyByIdQueryVariables,
	PropertyImagesQuery,
	PropertyImagesQueryVariables,
	PropertyCostsQuery,
	PropertyCostsQueryVariables,
	PropertyFeaturesQuery,
	PropertyFeaturesQueryVariables,
} from "@/api/graphql-operations-types.js";
import { executeGraphQL } from "@/api/graphqlClient.js";

// ---- Listing by Id ----
const LISTING_QUERY = gql`
	query ListingById($listingId: ID!) {
		uiapi {
			query {
				Property_Listing__c(where: { Id: { eq: $listingId } }, first: 1) {
					edges {
						node {
							Id
							Name @optional {
								value
								displayValue
							}
							Listing_Price__c @optional {
								value
								displayValue
							}
							Listing_Status__c @optional {
								value
								displayValue
							}
							Property__c @optional {
								value
								displayValue
							}
						}
					}
				}
			}
		}
	}
`;

export interface ListingDetail {
	id: string;
	name: string | null;
	listingPrice: number | string | null;
	listingStatus: string | null;
	propertyId: string | null;
}

export async function fetchListingById(listingId: string): Promise<ListingDetail | null> {
	const variables: ListingByIdQueryVariables = { listingId };
	const res = await executeGraphQL<ListingByIdQuery, ListingByIdQueryVariables>(
		LISTING_QUERY,
		variables,
	);
	const node = res.uiapi?.query?.Property_Listing__c?.edges?.[0]?.node;
	if (!node) return null;
	const prop = node.Property__c;
	return {
		id: node.Id,
		name: node.Name?.value != null ? String(node.Name.value) : (node.Name?.displayValue ?? null),
		listingPrice:
			node.Listing_Price__c?.value != null
				? ((typeof node.Listing_Price__c.value === "number"
						? node.Listing_Price__c.value
						: node.Listing_Price__c.displayValue) ?? null)
				: null,
		listingStatus:
			node.Listing_Status__c?.value != null
				? String(node.Listing_Status__c.value)
				: (node.Listing_Status__c?.displayValue ?? null),
		propertyId: prop?.value != null ? String(prop.value) : (prop?.displayValue ?? null),
	};
}

// ---- Property by Id ----
const PROPERTY_QUERY = gql`
	query PropertyById($propertyId: ID!) {
		uiapi {
			query {
				Property__c(where: { Id: { eq: $propertyId } }, first: 1) {
					edges {
						node {
							Id
							Name @optional {
								value
								displayValue
							}
							Address__c @optional {
								value
								displayValue
							}
							Coordinates__Latitude__s @optional {
								value
								displayValue
							}
							Coordinates__Longitude__s @optional {
								value
								displayValue
							}
							Type__c @optional {
								value
								displayValue
							}
							Monthly_Rent__c @optional {
								value
								displayValue
							}
							Bedrooms__c @optional {
								value
								displayValue
							}
							Bathrooms__c @optional {
								value
								displayValue
							}
							Sq_Ft__c @optional {
								value
								displayValue
							}
							Description__c @optional {
								value
								displayValue
							}
						}
					}
				}
			}
		}
	}
`;

export interface PropertyDetail {
	id: string;
	name: string | null;
	address: string | null;
	propertyType: string | null;
	monthlyRent: number | string | null;
	bedrooms: number | string | null;
	bathrooms: number | string | null;
	squareFootage: number | string | null;
	description: string | null;
	coordinates: {
		lat: number | null;
		lng: number | null;
	} | null;
}

export async function fetchPropertyById(propertyId: string): Promise<PropertyDetail | null> {
	const variables: PropertyByIdQueryVariables = { propertyId };
	const res = await executeGraphQL<PropertyByIdQuery, PropertyByIdQueryVariables>(
		PROPERTY_QUERY,
		variables,
	);
	const node = res.uiapi?.query?.Property__c?.edges?.[0]?.node;
	if (!node) return null;
	const v = (f: { value?: unknown; displayValue?: string | null } | null | undefined) =>
		f?.value != null
			? typeof f.value === "number"
				? f.value
				: String(f.value)
			: (f?.displayValue ?? null);
	return {
		id: node.Id,
		name: node.Name?.value != null ? String(node.Name.value) : (node.Name?.displayValue ?? null),
		address:
			node.Address__c?.value != null
				? String(node.Address__c.value)
				: (node.Address__c?.displayValue ?? null),
		propertyType:
			node.Type__c?.value != null
				? String(node.Type__c.value)
				: (node.Type__c?.displayValue ?? null),
		monthlyRent: v(node.Monthly_Rent__c),
		bedrooms: v(node.Bedrooms__c),
		bathrooms: v(node.Bathrooms__c),
		squareFootage: v(node.Sq_Ft__c),
		description:
			node.Description__c?.value != null
				? String(node.Description__c.value)
				: (node.Description__c?.displayValue ?? null),
		coordinates:
			node.Coordinates__Latitude__s && node.Coordinates__Longitude__s
				? {
						lat:
							typeof node.Coordinates__Latitude__s.value === "number"
								? node.Coordinates__Latitude__s.value
								: node.Coordinates__Latitude__s.displayValue != null
									? Number(node.Coordinates__Latitude__s.displayValue)
									: null,
						lng:
							typeof node.Coordinates__Longitude__s.value === "number"
								? node.Coordinates__Longitude__s.value
								: node.Coordinates__Longitude__s.displayValue != null
									? Number(node.Coordinates__Longitude__s.displayValue)
									: null,
					}
				: null,
	};
}

/** Fetch Address__c for multiple properties (for map markers). Returns id -> address. */
export async function fetchPropertyAddresses(
	propertyIds: string[],
): Promise<Record<string, string>> {
	const uniq = [...new Set(propertyIds)].filter(Boolean);
	const entries = await Promise.all(
		uniq.map(async (id) => {
			const p = await fetchPropertyById(id);
			return p?.address ? ([id, p.address] as const) : null;
		}),
	);
	return Object.fromEntries(entries.filter((e): e is [string, string] => e != null));
}

// ---- Property Images by Property Id ----
const IMAGES_QUERY = gql`
	query PropertyImages($propertyId: ID!) {
		uiapi {
			query {
				Property_Image__c(where: { Property__c: { eq: $propertyId } }, first: 50) {
					edges {
						node {
							Id
							Name @optional {
								value
								displayValue
							}
							Image_URL__c @optional {
								value
								displayValue
							}
							Image_Type__c @optional {
								value
								displayValue
							}
							Display_Order__c @optional {
								value
								displayValue
							}
							Alt_Text__c @optional {
								value
								displayValue
							}
						}
					}
				}
			}
		}
	}
`;

export interface PropertyImageRecord {
	id: string;
	name: string | null;
	imageUrl: string | null;
	imageType: string | null;
	displayOrder: number | null;
	altText: string | null;
}

export async function fetchImagesByPropertyId(propertyId: string): Promise<PropertyImageRecord[]> {
	const variables: PropertyImagesQueryVariables = { propertyId };
	const res = await executeGraphQL<PropertyImagesQuery, PropertyImagesQueryVariables>(
		IMAGES_QUERY,
		variables,
	);
	const edges = res.uiapi?.query?.Property_Image__c?.edges ?? [];
	const list: PropertyImageRecord[] = [];
	for (const e of edges) {
		const n = e?.node;
		if (!n) continue;
		const order = n.Display_Order__c?.value;
		list.push({
			id: n.Id,
			name: n.Name?.value != null ? String(n.Name.value) : (n.Name?.displayValue ?? null),
			imageUrl:
				n.Image_URL__c?.value != null
					? String(n.Image_URL__c.value)
					: (n.Image_URL__c?.displayValue ?? null),
			imageType:
				n.Image_Type__c?.value != null
					? String(n.Image_Type__c.value)
					: (n.Image_Type__c?.displayValue ?? null),
			displayOrder: typeof order === "number" ? order : order != null ? Number(order) : null,
			altText:
				n.Alt_Text__c?.value != null
					? String(n.Alt_Text__c.value)
					: (n.Alt_Text__c?.displayValue ?? null),
		});
	}
	list.sort((a, b) => (a.displayOrder ?? 0) - (b.displayOrder ?? 0));
	return list;
}

// ---- Property Costs by Property Id ----
const COSTS_QUERY = gql`
	query PropertyCosts($propertyId: ID!) {
		uiapi {
			query {
				Property_Cost__c(where: { Property__c: { eq: $propertyId } }, first: 100) {
					edges {
						node {
							Id
							Cost_Category__c @optional {
								value
								displayValue
							}
							Cost_Amount__c @optional {
								value
								displayValue
							}
							Cost_Date__c @optional {
								value
								displayValue
							}
							Description__c @optional {
								value
								displayValue
							}
							Vendor__c @optional {
								value
								displayValue
							}
						}
					}
				}
			}
		}
	}
`;

export interface PropertyCostRecord {
	id: string;
	category: string | null;
	amount: number | string | null;
	date: string | null;
	description: string | null;
	vendor: string | null;
}

export async function fetchCostsByPropertyId(propertyId: string): Promise<PropertyCostRecord[]> {
	const variables: PropertyCostsQueryVariables = { propertyId };
	const res = await executeGraphQL<PropertyCostsQuery, PropertyCostsQueryVariables>(
		COSTS_QUERY,
		variables,
	);
	const edges = res.uiapi?.query?.Property_Cost__c?.edges ?? [];
	const list: PropertyCostRecord[] = [];
	for (const e of edges) {
		const n = e?.node;
		if (!n) continue;
		const amt = n.Cost_Amount__c?.value;
		list.push({
			id: n.Id,
			category:
				n.Cost_Category__c?.value != null
					? String(n.Cost_Category__c.value)
					: (n.Cost_Category__c?.displayValue ?? null),
			amount:
				typeof amt === "number"
					? amt
					: amt != null
						? Number(amt)
						: (n.Cost_Amount__c?.displayValue ?? null),
			date:
				n.Cost_Date__c?.value != null
					? String(n.Cost_Date__c.value)
					: (n.Cost_Date__c?.displayValue ?? null),
			description:
				n.Description__c?.value != null
					? String(n.Description__c.value)
					: (n.Description__c?.displayValue ?? null),
			vendor:
				n.Vendor__c?.value != null
					? String(n.Vendor__c.value)
					: (n.Vendor__c?.displayValue ?? null),
		});
	}
	return list;
}

// ---- Property Features by Property Id ----
const FEATURES_QUERY = gql`
	query PropertyFeatures($propertyId: ID!) {
		uiapi {
			query {
				Property_Feature__c(where: { Property__c: { eq: $propertyId } }, first: 100) {
					edges {
						node {
							Id
							Name @optional {
								value
								displayValue
							}
							Feature_Category__c @optional {
								value
								displayValue
							}
							Description__c @optional {
								value
								displayValue
							}
						}
					}
				}
			}
		}
	}
`;

export interface PropertyFeatureRecord {
	id: string;
	name: string | null;
	category: string | null;
	description: string | null;
}

export async function fetchFeaturesByPropertyId(
	propertyId: string,
): Promise<PropertyFeatureRecord[]> {
	const variables: PropertyFeaturesQueryVariables = { propertyId };
	const res = await executeGraphQL<PropertyFeaturesQuery, PropertyFeaturesQueryVariables>(
		FEATURES_QUERY,
		variables,
	);
	const edges = res.uiapi?.query?.Property_Feature__c?.edges ?? [];
	const list: PropertyFeatureRecord[] = [];
	for (const e of edges) {
		const n = e?.node;
		if (!n) continue;
		list.push({
			id: n.Id,
			name: n.Name?.value != null ? String(n.Name.value) : (n.Name?.displayValue ?? null),
			category:
				n.Feature_Category__c?.value != null
					? String(n.Feature_Category__c.value)
					: (n.Feature_Category__c?.displayValue ?? null),
			description:
				n.Description__c?.value != null
					? String(n.Description__c.value)
					: (n.Description__c?.displayValue ?? null),
		});
	}
	return list;
}

/**
 * Fetch primary image URL per property (for search result thumbnails).
 * Returns a map of propertyId -> image URL. Uses first Image_Type__c = 'Primary' or first image.
 */
export async function fetchPrimaryImagesByPropertyIds(
	propertyIds: string[],
): Promise<Record<string, string>> {
	const map: Record<string, string> = {};
	const uniq = [...new Set(propertyIds)].filter(Boolean);
	for (const id of uniq) {
		const images = await fetchImagesByPropertyId(id);
		const primary = images.find((i) => i.imageType === "Primary") ?? images[0];
		if (primary?.imageUrl) map[id] = primary.imageUrl;
	}
	return map;
}
