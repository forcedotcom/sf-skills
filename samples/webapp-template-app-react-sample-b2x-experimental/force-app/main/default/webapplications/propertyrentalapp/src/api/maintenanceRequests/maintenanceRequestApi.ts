/**
 * Maintenance_Request__c: list via GraphQL, create via createRecord.
 */
import { createRecord } from "@salesforce/webapp-experimental/api";
import { gql } from "@salesforce/sdk-data";
import type {
	MaintenanceRequestsQuery,
	MaintenanceRequestsQueryVariables,
} from "@/api/graphql-operations-types.js";
import { executeGraphQL } from "@/api/graphqlClient.js";

const OBJECT_API_NAME = "Maintenance_Request__c";

export interface MaintenanceRequestSummary {
	id: string;
	name: string | null;
	title: string | null;
	description: string | null;
	type: string | null;
	priority: string | null;
	status: string | null;
	dateRequested: string | null;
	/** Tenant / user the request is assigned to (from User__r lookup). */
	tenantName: string | null;
	/** Property address (from Property__r) for display; first part used in list like B2E. */
	propertyAddress: string | null;
}

function pick<T>(obj: T, key: keyof T): unknown {
	const v = obj[key];
	if (v != null && typeof v === "object" && "value" in v) {
		return (v as { value?: unknown }).value ?? null;
	}
	return v ?? null;
}

function str(x: unknown): string | null {
	if (x == null) return null;
	return String(x);
}

/** Node shape from MaintenanceRequests query (matches graphql-operations-types). */
interface MaintenanceRequestNode {
	Id: string;
	ApiName?: string | null;
	Name?: { value?: unknown; displayValue?: string | null } | null;
	Description__c?: { value?: unknown; displayValue?: string | null } | null;
	Type__c?: { value?: unknown; displayValue?: string | null } | null;
	Priority__c?: { value?: unknown; displayValue?: string | null } | null;
	Status__c?: { value?: unknown; displayValue?: string | null } | null;
	Scheduled__c?: { value?: unknown; displayValue?: string | null } | null;
	User__r?: { Name?: { value?: unknown; displayValue?: string | null } | null } | null;
	Property__r?: {
		Address__c?: { value?: unknown; displayValue?: string | null } | null;
	} | null;
}

function nodeToSummary(node: MaintenanceRequestNode): MaintenanceRequestSummary {
	const desc = str(pick(node, "Description__c"));
	const userRef = node.User__r as
		| { Name?: { value?: unknown; displayValue?: string | null } }
		| undefined;
	const tenantName =
		str(
			userRef?.Name && typeof userRef.Name === "object"
				? (userRef.Name as { value?: unknown }).value
				: null,
		) ??
		str(userRef?.Name?.displayValue) ??
		null;
	const propertyAddress =
		str(
			node.Property__r?.Address__c && typeof node.Property__r.Address__c === "object"
				? (node.Property__r.Address__c as { value?: unknown }).value
				: null,
		) ??
		str(node.Property__r?.Address__c?.displayValue) ??
		null;

	return {
		id: node.Id,
		name:
			str(pick(node, "Name")) ?? str((node.Name as { displayValue?: string | null })?.displayValue),
		title: desc,
		description: desc,
		type: str(pick(node, "Type__c")),
		priority: str(pick(node, "Priority__c")),
		status: str(pick(node, "Status__c")),
		dateRequested: str(pick(node, "Scheduled__c")),
		tenantName,
		propertyAddress,
	};
}

const MAINTENANCE_REQUESTS_QUERY = gql`
	query MaintenanceRequests($first: Int!, $after: String) {
		uiapi {
			query {
				Maintenance_Request__c(first: $first, after: $after) {
					edges {
						node {
							Id
							ApiName
							Name @optional {
								value
								displayValue
							}
							Description__c @optional {
								value
								displayValue
							}
							Type__c @optional {
								value
								displayValue
							}
							Priority__c @optional {
								value
								displayValue
							}
							Status__c @optional {
								value
								displayValue
							}
							Scheduled__c @optional {
								value
								displayValue
							}
							User__r @optional {
								Name @optional {
									value
									displayValue
								}
							}
							Property__r @optional {
								Address__c @optional {
									value
									displayValue
								}
							}
						}
						cursor
					}
					pageInfo {
						hasNextPage
						endCursor
					}
				}
			}
		}
	}
`;

export async function queryMaintenanceRequests(
	first: number = 50,
	after: string | null = null,
): Promise<MaintenanceRequestSummary[]> {
	const variables: MaintenanceRequestsQueryVariables = { first, after: after ?? null };
	const response = await executeGraphQL<
		MaintenanceRequestsQuery,
		MaintenanceRequestsQueryVariables
	>(MAINTENANCE_REQUESTS_QUERY, variables);
	const edges = response.uiapi?.query?.Maintenance_Request__c?.edges ?? [];
	const list: MaintenanceRequestSummary[] = [];
	for (const e of edges) {
		if (e?.node) list.push(nodeToSummary(e.node as MaintenanceRequestNode));
	}
	// Sort by date requested descending (newest first)
	list.sort((a, b) => {
		const da = a.dateRequested ?? "";
		const db = b.dateRequested ?? "";
		return db.localeCompare(da);
	});
	return list;
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
