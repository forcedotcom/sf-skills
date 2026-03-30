/**
 * Maintenance_Request__c: list via GraphQL, create via createRecord.
 */
import { createRecord } from "@salesforce/ui-bundle/api";
import MAINTENANCE_REQUESTS_QUERY from "./query/maintenanceRequests.graphql?raw";
import type {
	MaintenanceRequestsQuery,
	MaintenanceRequestsQueryVariables,
} from "@/api/graphql-operations-types.js";
import {
	searchObjects,
	type ObjectSearchOptions,
} from "@/features/object-search/api/objectSearchService";

const OBJECT_API_NAME = "Maintenance_Request__c";

export type MaintenanceRequestSearchResult = NonNullable<
	MaintenanceRequestsQuery["uiapi"]["query"]["Maintenance_Request__c"]
>;

export type MaintenanceRequestNode = NonNullable<
	NonNullable<NonNullable<MaintenanceRequestSearchResult["edges"]>[number]>["node"]
>;

export type MaintenanceRequestSearchOptions = ObjectSearchOptions<
	MaintenanceRequestsQueryVariables["where"],
	MaintenanceRequestsQueryVariables["orderBy"]
>;

export async function searchMaintenanceRequests(
	options: MaintenanceRequestSearchOptions = {},
): Promise<MaintenanceRequestSearchResult> {
	return searchObjects<
		MaintenanceRequestSearchResult,
		MaintenanceRequestsQuery,
		MaintenanceRequestsQueryVariables
	>(MAINTENANCE_REQUESTS_QUERY, OBJECT_API_NAME, options);
}

export interface CreateMaintenanceRequestInput {
	Description__c: string;
	Type__c?: string | null;
	Priority__c?: string;
	Status__c?: string;
	Scheduled__c?: string | null;
}

function getRecordIdFromResponse(result: Record<string, unknown>): string {
	const id =
		typeof result.id === "string"
			? result.id
			: (result.fields as Record<string, { value?: string }> | undefined)?.Id?.value;
	if (!id) throw new Error("Create succeeded but no record id returned");
	return id;
}

export async function createMaintenanceRequest(
	input: CreateMaintenanceRequestInput,
): Promise<{ id: string }> {
	const description = input.Description__c?.trim();
	if (!description) throw new Error("Description is required");
	const fields: Record<string, unknown> = {
		Description__c: description,
		Priority__c: input.Priority__c?.trim() || "Standard",
		Status__c: input.Status__c?.trim() || "New",
	};
	if (input.Type__c?.trim()) fields.Type__c = input.Type__c.trim();
	if (input.Scheduled__c?.trim()) fields.Scheduled__c = input.Scheduled__c.trim();
	const result = (await createRecord(OBJECT_API_NAME, fields)) as unknown as Record<
		string,
		unknown
	>;
	return { id: getRecordIdFromResponse(result) };
}
