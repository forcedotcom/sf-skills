/**
 * Create Application__c (property application) record via Salesforce UI API.
 * Uses User__c to link the application to the authenticated user.
 */
import { createRecord } from "@salesforce/webapp-experimental/api";

const OBJECT_API_NAME = "Application__c";

export interface ApplicationRecordInput {
	Property__c: string | null;
	User__c: string;
	Status__c?: string;
	Start_Date__c?: string | null;
	Employment__c?: string | null;
	References__c?: string | null;
}

export async function createApplicationRecord(
	input: ApplicationRecordInput,
): Promise<{ id: string }> {
	const fields: Record<string, unknown> = {};

	if (input.Property__c != null && input.Property__c !== "") {
		fields.Property__c = input.Property__c;
	}
	if (input.User__c) {
		fields.User__c = input.User__c;
	}
	if (input.Status__c != null && input.Status__c !== "") {
		fields.Status__c = input.Status__c;
	}
	if (input.Start_Date__c != null && input.Start_Date__c !== "") {
		fields.Start_Date__c = input.Start_Date__c;
	}
	if (input.Employment__c != null && input.Employment__c !== "") {
		fields.Employment__c = input.Employment__c;
	}
	if (input.References__c != null && input.References__c !== "") {
		fields.References__c = input.References__c;
	}

	const result = (await createRecord(OBJECT_API_NAME, fields)) as unknown as Record<
		string,
		unknown
	>;
	const id =
		typeof result.id === "string"
			? result.id
			: (result.fields as Record<string, { value?: string }> | undefined)?.Id?.value;
	if (!id) {
		throw new Error("Create succeeded but no record id returned");
	}
	return { id };
}
