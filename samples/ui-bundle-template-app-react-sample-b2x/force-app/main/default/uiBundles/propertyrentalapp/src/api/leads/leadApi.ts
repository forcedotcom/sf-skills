/**
 * Create Lead records in Salesforce for Contact Us form and newsletter signup.
 * Uses the standard Lead object (FirstName, LastName, Email, Phone, Company, Description, LeadSource).
 */
import { createRecord } from "@salesforce/ui-bundle/api";

const OBJECT_API_NAME = "Lead";

const LEAD_SOURCE_WEBSITE = "Website";
const LEAD_SOURCE_NEWSLETTER = "Website Newsletter";

function getRecordIdFromResponse(result: Record<string, unknown>): string {
	const id =
		typeof result.id === "string"
			? result.id
			: (result.fields as Record<string, { value?: string }> | undefined)?.Id?.value;
	if (!id) throw new Error("Create succeeded but no record id returned");
	return id;
}

export interface ContactUsInput extends UserInfo {
	Subject?: string;
	Message: string;
}

export interface UserInfo {
	FirstName: string;
	LastName: string;
	Email: string;
	Phone?: string;
}

/**
 * Creates a Lead from the Contact Us form. Uses Company for subject, Description for message.
 */
export async function createContactUsLead(input: ContactUsInput): Promise<{ id: string }> {
	const fields: Record<string, unknown> = {
		Company: (input.Subject ?? "Contact Us").trim() || "Contact Us",
		Description: input.Message.trim() || "",
		LeadSource: LEAD_SOURCE_WEBSITE,
	};
	if (input.FirstName?.trim()) {
		fields.FirstName = input.FirstName.trim();
	}
	if (input.LastName?.trim()) {
		fields.LastName = input.LastName.trim();
	}
	if (input.Email?.trim()) {
		fields.Email = input.Email.trim();
	}
	if (input.Phone?.trim()) {
		fields.Phone = input.Phone.trim();
	}
	const result = (await createRecord(OBJECT_API_NAME, fields)) as unknown as Record<
		string,
		unknown
	>;
	return { id: getRecordIdFromResponse(result) };
}

/**
 * Creates a Lead for newsletter/email signup. LastName and Company set to placeholders so Lead is valid.
 */
export async function createNewsletterLead(email: string): Promise<{ id: string }> {
	const trimmed = email.trim();
	if (!trimmed) throw new Error("Email is required");
	const fields: Record<string, unknown> = {
		LastName: "Newsletter Subscriber",
		Company: "Website",
		Email: trimmed,
		LeadSource: LEAD_SOURCE_NEWSLETTER,
	};
	const result = (await createRecord(OBJECT_API_NAME, fields)) as unknown as Record<
		string,
		unknown
	>;
	return { id: getRecordIdFromResponse(result) };
}
