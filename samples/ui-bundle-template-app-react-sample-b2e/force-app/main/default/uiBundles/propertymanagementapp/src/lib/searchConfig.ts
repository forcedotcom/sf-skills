/**
 * Property-management search configuration for feature-react-search.
 *
 * The search feature builds its GraphQL queries at runtime from this config, so
 * the app no longer ships per-object `.graphql` search documents or
 * `searchObjects()` services. One `SearchConfig` describes all four searchable
 * objects; `<UnifiedSearch>` consumes it for both the unified `/search` page and
 * each single-object page (via `restrictTo`).
 *
 * `displayFields` must cover every field the result cards and detail modals read
 * — see the matching `*SearchNode` types in `src/api/**`. Relationships that
 * require arguments (e.g. `ContentDocumentLinks(first: 1)` thumbnails or the
 * worker's open-request `totalCount`) cannot be expressed here and are
 * intentionally omitted; the cards degrade gracefully when they are absent.
 */

import type { SearchConfig } from "../features/search";

/** Stable source keys — used as GraphQL aliases, URL namespaces, and result-map keys. */
export const SOURCE_KEYS = {
	PROPERTIES: "properties",
	MAINTENANCE: "maintenance",
	WORKERS: "workers",
	APPLICATIONS: "applications",
} as const;

export type SourceKey = (typeof SOURCE_KEYS)[keyof typeof SOURCE_KEYS];

/** Page-size options shared by every source (cards lay out 3-up). */
export const SEARCH_PAGE_SIZE = 6;
export const SEARCH_PAGE_SIZE_OPTIONS = [6, 12, 24, 48];

export const searchConfig: SearchConfig = {
	// One global pagination config — the single source of truth for the whole
	// search experience. `merged` mode windows the cumulative result set into
	// fixed pages of `pageSize`, and `proportional` spreads each object type by
	// its result count so larger sources appear more often. These settings apply
	// to every object type, in every scope — the unified `/search` page, when the
	// dropdown narrows to one source, and single-object pages (via `restrictTo`).
	pagination: {
		mode: "merged",
		mergeOrder: "proportional",
		pageSize: SEARCH_PAGE_SIZE,
		pageSizeOptions: SEARCH_PAGE_SIZE_OPTIONS,
	},
	sources: [
		{
			kind: "sobject",
			key: SOURCE_KEYS.PROPERTIES,
			objectName: "Property__c",
			label: "Properties",
			labelSingular: "Property",
			searchableFields: ["Name", "Address__c"],
			displayFields: [
				"Name",
				"Address__c",
				"Status__c",
				"Type__c",
				"Monthly_Rent__c",
				"Bedrooms__c",
				"Bathrooms__c",
				"Description__c",
				"Hero_Image__c",
				"Sq_Ft__c",
				"Year_Built__c",
				"Deposit__c",
				"Parking__c",
				"Pet_Friendly__c",
				"Available_Date__c",
				"Lease_Term__c",
				"Features__c",
				"Utilities__c",
				"Tour_URL__c",
				"CreatedDate",
			],
			filterBy: [
				{ field: "Status__c", label: "Status", type: "multipicklist" },
				{ field: "Type__c", label: "Type", type: "multipicklist" },
				{ field: "Monthly_Rent__c", label: "Monthly Rent", type: "numeric" },
				{ field: "Bedrooms__c", label: "Bedrooms", type: "numeric" },
			],
			sortBy: [
				{ field: "Name", label: "Name" },
				{ field: "Monthly_Rent__c", label: "Monthly Rent" },
				{ field: "Status__c", label: "Status" },
				{ field: "CreatedDate", label: "Created Date" },
			],
		},
		{
			kind: "sobject",
			key: SOURCE_KEYS.MAINTENANCE,
			objectName: "Maintenance_Request__c",
			label: "Maintenance Requests",
			labelSingular: "Maintenance Request",
			searchableFields: [
				"Name",
				"User__r.Name",
				"Property__r.Address__c",
				"Assigned_Worker__r.Name",
			],
			displayFields: [
				"Name",
				"Description__c",
				"Type__c",
				"Priority__c",
				"Status__c",
				"Scheduled__c",
				{ name: "Property__r", subfields: ["Address__c", "Name"] },
				{ name: "User__r", subfields: ["Name"] },
				{ name: "Assigned_Worker__r", subfields: ["Name"] },
			],
			filterBy: [
				{ field: "Status__c", label: "Status", type: "multipicklist" },
				{ field: "Type__c", label: "Type", type: "multipicklist" },
				{ field: "Priority__c", label: "Priority", type: "multipicklist" },
				{ field: "Scheduled__c", label: "Scheduled", type: "datetime" },
			],
			sortBy: [
				{ field: "Name", label: "Subject" },
				{ field: "Status__c", label: "Status" },
				{ field: "Priority__c", label: "Priority" },
				{ field: "Scheduled__c", label: "Scheduled" },
				{ field: "CreatedDate", label: "Created Date" },
			],
			defaultSort: { field: "CreatedDate", direction: "DESC" },
		},
		{
			kind: "sobject",
			key: SOURCE_KEYS.WORKERS,
			objectName: "Maintenance_Worker__c",
			label: "Maintenance Workers",
			labelSingular: "Maintenance Worker",
			searchableFields: ["Name", "Phone__c"],
			displayFields: [
				"Name",
				"Type__c",
				"Employment_Type__c",
				"Phone__c",
				"Location__c",
				"IsActive__c",
				"Rating__c",
				"Hourly_Rate__c",
				"CreatedDate",
			],
			filterBy: [
				{ field: "Employment_Type__c", label: "Employment Type", type: "multipicklist" },
				{ field: "Location__c", label: "Location", type: "text", placeholder: "Location" },
				{ field: "Hourly_Rate__c", label: "Hourly Rate", type: "numeric" },
				{ field: "CreatedDate", label: "Created Date", type: "datetime" },
			],
			sortBy: [
				{ field: "Name", label: "Name" },
				{ field: "Employment_Type__c", label: "Employment Type" },
				{ field: "Hourly_Rate__c", label: "Hourly Rate" },
				{ field: "Rating__c", label: "Rating" },
				{ field: "CreatedDate", label: "Created Date" },
			],
		},
		{
			kind: "sobject",
			key: SOURCE_KEYS.APPLICATIONS,
			objectName: "Application__c",
			label: "Applications",
			labelSingular: "Application",
			searchableFields: ["Name", "User__r.Name", "Property__r.Address__c"],
			displayFields: [
				"Name",
				"Status__c",
				"Start_Date__c",
				"Employment__c",
				"References__c",
				{ name: "Property__r", subfields: ["Name", "Address__c"] },
				{ name: "User__r", subfields: ["Name"] },
				"CreatedDate",
			],
			filterBy: [
				{ field: "Status__c", label: "Status", type: "multipicklist" },
				{ field: "Start_Date__c", label: "Start Date", type: "date" },
				{ field: "CreatedDate", label: "Created Date", type: "datetime" },
			],
			sortBy: [
				{ field: "Name", label: "Application" },
				{ field: "Status__c", label: "Status" },
				{ field: "Start_Date__c", label: "Start Date" },
				{ field: "CreatedDate", label: "Created Date" },
			],
			defaultSort: { field: "CreatedDate", direction: "DESC" },
		},
	],
};
