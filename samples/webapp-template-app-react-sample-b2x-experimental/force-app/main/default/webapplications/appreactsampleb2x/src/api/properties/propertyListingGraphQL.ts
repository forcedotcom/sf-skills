/**
 * Property Listing search via Salesforce GraphQL.
 * Replaces REST keyword search with uiapi.query.Property_Listing__c.
 */
import { gql } from "@salesforce/sdk-data";
import type {
	PropertyListingsQuery,
	PropertyListingsQueryVariables,
} from "@/api/graphql-operations-types.js";
import { ResultOrder } from "@/api/graphql-operations-types.js";
import { executeGraphQL } from "@/api/graphqlClient.js";
import type {
	SearchResultRecord,
	SearchResultRecordData,
	FieldValue,
} from "@/types/searchResults.js";

const OBJECT_API_NAME = "Property_Listing__c";

/** GraphQL node shape: fields are { value?, displayValue? }. Property__r for property name and location. */
type PropertyListingNode = {
	Id: string;
	ApiName?: string | null;
	Name?: { value?: string | null; displayValue?: string | null } | null;
	Listing_Price__c?: { value?: number | null; displayValue?: string | null } | null;
	Listing_Status__c?: { value?: string | null; displayValue?: string | null } | null;
	Property__c?: { value?: string | null; displayValue?: string | null } | null;
	Property__r?: {
		Name?: { value?: string | null; displayValue?: string | null } | null;
		Address__c?: { value?: string | null; displayValue?: string | null } | null;
		Bedrooms__c?: { value?: number | null; displayValue?: string | null } | null;
	} | null;
};

function nodeToFieldValue(
	fieldObj: { value?: unknown; displayValue?: string | null } | null | undefined,
): FieldValue {
	if (fieldObj == null) {
		return { displayValue: null, value: null };
	}
	const value = fieldObj.value ?? null;
	const displayValue = fieldObj.displayValue ?? (value != null ? String(value) : null);
	return { displayValue, value };
}

function nodeToSearchResultRecordData(node: PropertyListingNode): SearchResultRecordData {
	const fields: Record<string, FieldValue> = {};
	const fieldKeys: (keyof PropertyListingNode)[] = [
		"Name",
		"Listing_Price__c",
		"Listing_Status__c",
		"Property__c",
	];
	for (const key of fieldKeys) {
		if (key === "Id" || key === "ApiName") continue;
		const raw = node[key];
		if (raw != null && typeof raw === "object" && "value" in raw) {
			fields[key] = nodeToFieldValue(raw as { value?: unknown; displayValue?: string | null });
		}
	}
	// Flatten property name and address for display (read-only fields for search results)
	const prop = node.Property__r;
	if (prop?.Name != null && typeof prop.Name === "object" && "value" in prop.Name) {
		fields["Property__r.Name"] = nodeToFieldValue(
			prop.Name as { value?: unknown; displayValue?: string | null },
		);
	}
	if (
		prop?.Address__c != null &&
		typeof prop.Address__c === "object" &&
		"value" in prop.Address__c
	) {
		fields["Property__r.Address__c"] = nodeToFieldValue(
			prop.Address__c as { value?: unknown; displayValue?: string | null },
		);
	}
	if (
		prop?.Bedrooms__c != null &&
		typeof prop.Bedrooms__c === "object" &&
		"value" in prop.Bedrooms__c
	) {
		fields["Property__r.Bedrooms__c"] = nodeToFieldValue(
			prop.Bedrooms__c as { value?: unknown; displayValue?: string | null },
		);
	}
	return {
		id: node.Id,
		apiName: typeof node.ApiName === "string" ? node.ApiName : OBJECT_API_NAME,
		eTag: "",
		fields,
		childRelationships: {},
		weakEtag: 0,
	};
}

/** Query with optional search term (Name like), pagination, and orderBy.
 * Uses Property_Listing__c_Filter. orderBy is optional; omit if org schema does not support it. */
const PROPERTY_LISTINGS_QUERY = gql`
	query PropertyListings(
		$where: Property_Listing__c_Filter
		$first: Int!
		$after: String
		$orderBy: Property_Listing__c_OrderBy
	) {
		uiapi {
			query {
				Property_Listing__c(where: $where, first: $first, after: $after, orderBy: $orderBy) {
					edges {
						node {
							Id
							ApiName
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
							Property__r @optional {
								Name @optional {
									value
									displayValue
								}
								Address__c @optional {
									value
									displayValue
								}
								Bedrooms__c @optional {
									value
									displayValue
								}
							}
						}
						cursor
					}
					pageInfo {
						hasNextPage
						hasPreviousPage
						startCursor
						endCursor
					}
					totalCount
				}
			}
		}
	}
`;

export interface PropertyListingGraphQLResult {
	records: SearchResultRecord[];
	nextPageToken: string | null;
	previousPageToken: string | null;
	endCursor: string | null;
	totalCount: number | null;
}

/** SortBy values match PropertySearchFilters SortBy (price_asc, price_desc, beds_asc, beds_desc). */
export interface PropertyListingFilters {
	priceMin?: number;
	priceMax?: number;
	bedroomsMin?: number;
	bedroomsMax?: number;
	sortBy?: "price_asc" | "price_desc" | "beds_asc" | "beds_desc" | null;
}

/** Where condition for Property_Listing__c_Filter (matches graphql-operations-types.ts). */
type PropertyListingsWhereCondition = {
	Name?: { like: string };
	Listing_Status__c?: { like: string };
	Listing_Price__c?: { gte?: number; lte?: number };
	Property__r?: {
		Name?: { like: string };
		Address__c?: { like: string };
		Bedrooms__c?: { gte?: number; lte?: number };
	};
};

/** Text search: name or Property__r name/address. Returns { or: [...] } or undefined. */
function buildTextWhere(
	searchTerm: string,
): NonNullable<PropertyListingsQueryVariables["where"]> | undefined {
	const term = searchTerm.trim();
	if (term.length === 0) return undefined;
	const pattern = `%${term}%`;
	return {
		or: [
			{ Name: { like: pattern } },
			{ Property__r: { Name: { like: pattern } } },
			{ Property__r: { Address__c: { like: pattern } } },
		],
	};
}

/** Element type allowed inside { and: [...] } (no nested and). */
type AndElement = PropertyListingsWhereCondition | { or: PropertyListingsWhereCondition[] };

/** Combines text search + price range + bedroom range (min/max) into one where (and of conditions). */
function buildWhere(
	searchTerm: string,
	filters: PropertyListingFilters | undefined,
): PropertyListingsQueryVariables["where"] {
	const conditions: AndElement[] = [];
	const textWhere = buildTextWhere(searchTerm);
	if (textWhere) conditions.push(textWhere as AndElement);
	const priceMin =
		filters?.priceMin != null && Number.isFinite(filters.priceMin) ? filters.priceMin : undefined;
	const priceMax =
		filters?.priceMax != null && Number.isFinite(filters.priceMax) ? filters.priceMax : undefined;
	if (priceMin != null || priceMax != null) {
		conditions.push({
			Listing_Price__c: {
				...(priceMin != null && { gte: priceMin }),
				...(priceMax != null && { lte: priceMax }),
			},
		});
	}
	const bedroomsMin =
		filters?.bedroomsMin != null && Number.isFinite(filters.bedroomsMin) && filters.bedroomsMin >= 0
			? filters.bedroomsMin
			: undefined;
	const bedroomsMax =
		filters?.bedroomsMax != null && Number.isFinite(filters.bedroomsMax) && filters.bedroomsMax >= 0
			? filters.bedroomsMax
			: undefined;
	if (bedroomsMin != null || bedroomsMax != null) {
		conditions.push({
			Property__r: {
				Bedrooms__c: {
					...(bedroomsMin != null && { gte: bedroomsMin }),
					...(bedroomsMax != null && { lte: bedroomsMax }),
				},
			},
		});
	}
	if (conditions.length === 0) return undefined;
	if (conditions.length === 1) return conditions[0];
	return { and: conditions };
}

/** Build orderBy for Property_Listing__c from SortBy. Returns undefined when sortBy is null or not supported. */
function buildOrderBy(
	sortBy: PropertyListingFilters["sortBy"],
): PropertyListingsQueryVariables["orderBy"] {
	if (sortBy == null) return undefined;
	switch (sortBy) {
		case "price_asc":
			return { Listing_Price__c: { order: ResultOrder.Asc } };
		case "price_desc":
			return { Listing_Price__c: { order: ResultOrder.Desc } };
		case "beds_asc":
			return { Property__r: { Bedrooms__c: { order: ResultOrder.Asc } } };
		case "beds_desc":
			return { Property__r: { Bedrooms__c: { order: ResultOrder.Desc } } };
		default:
			return undefined;
	}
}

/**
 * Fetch Property_Listing__c records via GraphQL.
 * Optional text search (name, Property__r name/address), price range (min/max), and bedroom range (min/max).
 */
export async function queryPropertyListingsGraphQL(
	searchTerm: string,
	pageSize: number,
	afterCursor: string | null,
	_signal?: AbortSignal,
	filters?: PropertyListingFilters,
): Promise<PropertyListingGraphQLResult> {
	const where = buildWhere(searchTerm, filters);

	const variables: PropertyListingsQueryVariables = {
		first: Math.min(Math.max(pageSize, 1), 200),
	};
	if (where) variables.where = where;
	if (afterCursor) variables.after = afterCursor;
	const orderBy = buildOrderBy(filters?.sortBy);
	if (orderBy != null) variables.orderBy = orderBy;

	const response = await executeGraphQL<PropertyListingsQuery, PropertyListingsQueryVariables>(
		PROPERTY_LISTINGS_QUERY,
		variables,
	);

	const conn = response.uiapi?.query?.Property_Listing__c;
	const edges = conn?.edges ?? [];
	const pageInfo = conn?.pageInfo;

	const records: SearchResultRecord[] = edges
		.filter((e) => e != null && e.node != null)
		.map((e) => {
			const node = e!.node!;
			const data = nodeToSearchResultRecordData(node as PropertyListingNode);
			return {
				record: data,
				highlightInfo: { fields: {}, snippet: null },
				searchInfo: { isPromoted: false, isSpellCorrected: false },
			};
		});

	return {
		records,
		nextPageToken: pageInfo?.hasNextPage ? (pageInfo.endCursor ?? null) : null,
		previousPageToken: pageInfo?.hasPreviousPage ? (pageInfo.startCursor ?? null) : null,
		endCursor: pageInfo?.endCursor ?? null,
		totalCount: conn?.totalCount ?? null,
	};
}

/**
 * Fetch the available price range (min/max) from the first page of listings for the current search.
 * No price or bedroom filters applied. Used to render the filter bar with known bounds.
 */
export async function queryPropertyListingPriceRange(
	searchTerm: string,
): Promise<{ priceMin: number; priceMax: number } | null> {
	const where = buildTextWhere(searchTerm);
	const variables: PropertyListingsQueryVariables = {
		first: 200,
	};
	if (where) variables.where = where;

	const response = await executeGraphQL<PropertyListingsQuery, PropertyListingsQueryVariables>(
		PROPERTY_LISTINGS_QUERY,
		variables,
	);

	const edges = response.uiapi?.query?.Property_Listing__c?.edges ?? [];
	const prices: number[] = [];
	for (const edge of edges) {
		const node = edge?.node as PropertyListingNode | null | undefined;
		const raw = node?.Listing_Price__c?.value;
		const num = typeof raw === "number" && Number.isFinite(raw) ? raw : null;
		if (num != null && num >= 0) prices.push(num);
	}
	if (prices.length === 0) return null;
	return {
		priceMin: Math.min(...prices),
		priceMax: Math.max(...prices),
	};
}

/** Static columns for Property_Listing__c list (only fields exposed in the GraphQL query). */
export const PROPERTY_LISTING_COLUMNS = [
	{ fieldApiName: "Name", label: "Name", searchable: true, sortable: true },
	{ fieldApiName: "Listing_Price__c", label: "Listing Price", searchable: false, sortable: true },
	{ fieldApiName: "Listing_Status__c", label: "Status", searchable: false, sortable: true },
	{ fieldApiName: "Property__c", label: "Property", searchable: false, sortable: true },
] as const;
