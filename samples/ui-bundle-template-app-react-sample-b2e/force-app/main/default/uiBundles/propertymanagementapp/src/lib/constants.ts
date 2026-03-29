/**
 * Application-wide constants.
 */

import type { PaginationConfig } from "../features/object-search/hooks/useObjectSearchParams";

export const PAGE_SIZE_LIST = 12;
export const DASHBOARD_MAINTENANCE_LIMIT = 5;

export const PROPERTY_FILTER_EXCLUDED_FIELD_PATHS = new Set([
	"CreatedDate",
	"Hero_Image__c",
	"Year_Built__c",
	"Available_Date__c",
]);

export const MAINTENANCE_WORKER_FILTER_EXCLUDED_FIELD_PATHS = new Set<string>([]);
export const MAINTENANCE_FILTER_EXCLUDED_FIELD_PATHS = new Set(["Scheduled__c"]);
export const APPLICATION_FILTER_EXCLUDED_FIELD_PATHS = new Set<string>([]);

export const MAINTENANCE_WORKER_OBJECT_API_NAME = "Maintenance_Worker__c" as const;

export const FALLBACK_LABEL_PROPERTIES_PLURAL = "Properties";
export const FALLBACK_LABEL_MAINTENANCE_PLURAL = "Maintenance Requests";
export const FALLBACK_LABEL_MAINTENANCE_WORKERS_PLURAL = "Maintenance Workers";
export const FALLBACK_LABEL_APPLICATIONS_PLURAL = "Applications";

export const PROPERTY_OBJECT_API_NAME = "Property__c" as const;
export const MAINTENANCE_OBJECT_API_NAME = "Maintenance_Request__c" as const;
export const APPLICATION_OBJECT_API_NAME = "Application__c" as const;

export const SEARCHABLE_OBJECTS = [
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

export const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 6,
	validPageSizes: [6, 12, 24, 48],
};
