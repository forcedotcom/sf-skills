/**
 * Application-wide constants.
 */

const MAINTENANCE_WORKER_OBJECT_API_NAME = "Maintenance_Worker__c" as const;

const FALLBACK_LABEL_PROPERTIES_PLURAL = "Properties";
const FALLBACK_LABEL_MAINTENANCE_PLURAL = "Maintenance Requests";
const FALLBACK_LABEL_MAINTENANCE_WORKERS_PLURAL = "Maintenance Workers";
const FALLBACK_LABEL_APPLICATIONS_PLURAL = "Applications";

/**
 * Sentinel value for the "search across everything" option in the dashboard
 * search dropdown. Selecting it routes to the unified `/search` page rather
 * than a single-object list page.
 */
export const ALL_SEARCH_OBJECT_VALUE = "All" as const;

export const SEARCHABLE_OBJECTS = [
	{
		objectApiName: ALL_SEARCH_OBJECT_VALUE,
		path: "/search",
		fallbackLabelPlural: "All",
	},
	{
		objectApiName: "Property__c" as const,
		path: "/properties",
		fallbackLabelPlural: FALLBACK_LABEL_PROPERTIES_PLURAL,
	},
	{
		objectApiName: "Maintenance_Request__c" as const,
		path: "/maintenance/requests",
		fallbackLabelPlural: FALLBACK_LABEL_MAINTENANCE_PLURAL,
	},
	{
		objectApiName: MAINTENANCE_WORKER_OBJECT_API_NAME,
		path: "/maintenance/workers",
		fallbackLabelPlural: FALLBACK_LABEL_MAINTENANCE_WORKERS_PLURAL,
	},
	{
		objectApiName: "Application__c" as const,
		path: "/applications",
		fallbackLabelPlural: FALLBACK_LABEL_APPLICATIONS_PLURAL,
	},
] as const;

export type SearchableObjectConfig = (typeof SEARCHABLE_OBJECTS)[number];
