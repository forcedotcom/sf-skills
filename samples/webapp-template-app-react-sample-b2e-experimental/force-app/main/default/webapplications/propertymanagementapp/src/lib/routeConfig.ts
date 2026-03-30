/**
 * Central route configuration for list pages and navigation.
 * Use these paths for links and search redirects to avoid duplication.
 */
export const PATHS = {
	HOME: "/",
	PROPERTIES: "/properties",
	MAINTENANCE_REQUESTS: "/maintenance/requests",
	MAINTENANCE_WORKERS: "/maintenance/workers",
	APPLICATIONS: "/applications",
} as const;

export interface ListPageRoute {
	path: string;
	label: string;
	searchParamKey?: string;
}

/** List pages that appear in the Home search object dropdown and in nav */
export const LIST_PAGE_ROUTES: Record<string, ListPageRoute> = {
	properties: { path: PATHS.PROPERTIES, label: "Properties", searchParamKey: "q" },
	maintenance_requests: {
		path: PATHS.MAINTENANCE_REQUESTS,
		label: "Maintenance Requests",
		searchParamKey: "q",
	},
	maintenance_workers: {
		path: PATHS.MAINTENANCE_WORKERS,
		label: "Maintenance Workers",
		searchParamKey: "q",
	},
	applications: { path: PATHS.APPLICATIONS, label: "Applications", searchParamKey: "q" },
} as const;

export type ListPageKey = keyof typeof LIST_PAGE_ROUTES;
