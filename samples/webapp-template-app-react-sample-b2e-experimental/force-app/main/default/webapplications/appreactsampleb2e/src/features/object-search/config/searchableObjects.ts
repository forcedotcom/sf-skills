/**
 * Searchable object config for global search (e.g. Home page search bar).
 * Object API names, routes, and fallback labels for list/search pages.
 */
import {
	MAINTENANCE_WORKER_OBJECT_API_NAME,
	FALLBACK_LABEL_PROPERTIES_PLURAL,
	FALLBACK_LABEL_MAINTENANCE_PLURAL,
	FALLBACK_LABEL_MAINTENANCE_WORKERS_PLURAL,
	FALLBACK_LABEL_APPLICATIONS_PLURAL,
} from "../../../lib/constants";

export const PROPERTY_OBJECT_API_NAME = "Property__c" as const;
export const MAINTENANCE_OBJECT_API_NAME = "Maintenance_Request__c" as const;
export const APPLICATION_OBJECT_API_NAME = "Application__c" as const;
export { MAINTENANCE_WORKER_OBJECT_API_NAME };

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
