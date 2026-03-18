/**
 * Generated operation types for B2X GraphQL queries.
 * Regenerate with codegen (e.g. npm run graphql:codegen) when schema or operations change.
 */

// ---- MaintenanceRequests ----
export interface MaintenanceRequestsQueryVariables {
	first: number;
	after?: string | null;
}

export interface MaintenanceRequestsQuery {
	uiapi?: {
		query?: {
			Maintenance_Request__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						ApiName?: string | null;
						Name?: { value?: unknown; displayValue?: string | null } | null;
						Description__c?: { value?: unknown; displayValue?: string | null } | null;
						Type__c?: { value?: unknown; displayValue?: string | null } | null;
						Priority__c?: { value?: unknown; displayValue?: string | null } | null;
						Status__c?: { value?: unknown; displayValue?: string | null } | null;
						Scheduled__c?: { value?: unknown; displayValue?: string | null } | null;
						User__r?: {
							Name?: { value?: unknown; displayValue?: string | null } | null;
						} | null;
						Property__r?: {
							Address__c?: { value?: unknown; displayValue?: string | null } | null;
						} | null;
					} | null;
				}> | null;
				pageInfo?: {
					hasNextPage?: boolean | null;
					endCursor?: string | null;
				} | null;
			} | null;
		} | null;
	} | null;
}

// ---- PropertyListings ----
/** Single-field condition; Property__r filters on related Property (name, address, bedrooms). */
export type PropertyListingsWhereCondition = {
	Name?: { like: string };
	Listing_Status__c?: { like: string };
	Listing_Price__c?: { gte?: number; lte?: number };
	Property__r?: {
		Name?: { like: string };
		Address__c?: { like: string };
		Bedrooms__c?: { gte?: number };
	};
};
/** GraphQL ResultOrder values for orderBy (use ResultOrder.Asc / ResultOrder.Desc). */
export const ResultOrder = {
	Asc: "ASC",
	Desc: "DESC",
} as const;
export type ResultOrder = (typeof ResultOrder)[keyof typeof ResultOrder];

/** orderBy for Property_Listing__c (e.g. { Listing_Price__c: { order: ResultOrder.Asc } }). */
export type PropertyListingsOrderBy = {
	Listing_Price__c?: { order: ResultOrder };
	Property__r?: { Bedrooms__c?: { order: ResultOrder } };
};

/** Where clause: condition, or { and: conditions[] }, or { or: conditions[] }. */
export interface PropertyListingsQueryVariables {
	where?:
		| PropertyListingsWhereCondition
		| { and: Array<PropertyListingsWhereCondition | { or: PropertyListingsWhereCondition[] }> }
		| { or: PropertyListingsWhereCondition[] };
	first: number;
	after?: string | null;
	orderBy?: PropertyListingsOrderBy | null;
}

export interface PropertyListingsQuery {
	uiapi?: {
		query?: {
			Property_Listing__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						ApiName?: string | null;
						Name?: { value?: string | null; displayValue?: string | null } | null;
						Listing_Price__c?: {
							value?: number | null;
							displayValue?: string | null;
						} | null;
						Listing_Status__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Property__c?: { value?: string | null; displayValue?: string | null } | null;
						Property__r?: {
							Name?: { value?: string | null; displayValue?: string | null } | null;
							Address__c?: { value?: string | null; displayValue?: string | null } | null;
							Bedrooms__c?: { value?: number | null; displayValue?: string | null } | null;
						} | null;
					} | null;
					cursor?: string | null;
				}> | null;
				pageInfo?: {
					hasNextPage?: boolean | null;
					hasPreviousPage?: boolean | null;
					startCursor?: string | null;
					endCursor?: string | null;
				} | null;
				totalCount?: number | null;
			} | null;
		} | null;
	} | null;
}

// ---- ListingById ----
export interface ListingByIdQueryVariables {
	listingId: string;
}

export interface ListingByIdQuery {
	uiapi?: {
		query?: {
			Property_Listing__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null; displayValue?: string | null } | null;
						Listing_Price__c?: {
							value?: unknown;
							displayValue?: string | null;
						} | null;
						Listing_Status__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Property__c?: { value?: string | null; displayValue?: string | null } | null;
					} | null;
				}> | null;
			} | null;
		} | null;
	} | null;
}

// ---- PropertyById ----
export interface PropertyByIdQueryVariables {
	propertyId: string;
}

export interface PropertyByIdQuery {
	uiapi?: {
		query?: {
			Property__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null; displayValue?: string | null } | null;
						Address__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Type__c?: { value?: string | null; displayValue?: string | null } | null;
						Monthly_Rent__c?: {
							value?: unknown;
							displayValue?: string | null;
						} | null;
						Bedrooms__c?: { value?: unknown; displayValue?: string | null } | null;
						Bathrooms__c?: { value?: unknown; displayValue?: string | null } | null;
						Sq_Ft__c?: { value?: unknown; displayValue?: string | null } | null;
						Description__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
					} | null;
				}> | null;
			} | null;
		} | null;
	} | null;
}

// ---- PropertyImages ----
export interface PropertyImagesQueryVariables {
	propertyId: string;
}

export interface PropertyImagesQuery {
	uiapi?: {
		query?: {
			Property_Image__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null; displayValue?: string | null } | null;
						Image_URL__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Image_Type__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Display_Order__c?: {
							value?: unknown;
							displayValue?: string | null;
						} | null;
						Alt_Text__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
					} | null;
				}> | null;
			} | null;
		} | null;
	} | null;
}

// ---- PropertyCosts ----
export interface PropertyCostsQueryVariables {
	propertyId: string;
}

export interface PropertyCostsQuery {
	uiapi?: {
		query?: {
			Property_Cost__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Cost_Category__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Cost_Amount__c?: {
							value?: unknown;
							displayValue?: string | null;
						} | null;
						Cost_Date__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Description__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Vendor__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
					} | null;
				}> | null;
			} | null;
		} | null;
	} | null;
}

// ---- PropertyFeatures ----
export interface PropertyFeaturesQueryVariables {
	propertyId: string;
}

export interface PropertyFeaturesQuery {
	uiapi?: {
		query?: {
			Property_Feature__c?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null; displayValue?: string | null } | null;
						Feature_Category__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
						Description__c?: {
							value?: string | null;
							displayValue?: string | null;
						} | null;
					} | null;
				}> | null;
			} | null;
		} | null;
	} | null;
}

// ---- GetUserInfo ----
export interface GetUserInfoQuery {
	uiapi?: {
		query?: {
			User?: {
				edges?: Array<{
					node?: {
						Id: string;
						Name?: { value?: string | null } | null;
					} | null;
				}> | null;
			} | null;
		} | null;
	} | null;
}
