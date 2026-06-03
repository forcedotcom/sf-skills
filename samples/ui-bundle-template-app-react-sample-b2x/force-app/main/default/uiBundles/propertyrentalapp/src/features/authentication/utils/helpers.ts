/**
 * Error thrown when the API returns a non-OK response with structured error messages.
 * The `errors` array contains user-facing messages that are safe to display —
 * backend Apex classes guarantee that system exceptions are never exposed.
 */
export class ApiError extends Error {
	errors: string[];
	constructor(errors: string[]) {
		super(errors[0]);
		this.name = "ApiError";
		this.errors = errors;
	}
}

/**
 * [Dev Note] Helper to parse the fetch Response.
 * It handles the distinction between success (JSON) and failure (throwing Error).
 */
export async function handleApiResponse<T = unknown>(response: Response): Promise<T> {
	// 1. Robustness: Handle 204 No Content gracefully
	if (response.status === 204) {
		return {} as T;
	}

	let data: any = null;

	const contentType = response.headers.get("content-type");
	if (contentType?.includes("application/json")) {
		data = await response.json();
	} else {
		// [Dev Note] If Salesforce returns HTML (e.g. standard error page),
		// we consume text to avoid parsing errors.
		await response.text();
	}

	if (!response.ok) {
		console.error("API request failed", data);
		if (data?.errors?.length) {
			throw new ApiError(data.errors);
		}
		throw new Error("An unexpected error occurred");
	}

	return data as T;
}

/**
 * UI API Record response structure.
 */
export type RecordResponse = {
	fields: Record<
		string,
		{
			value: string;
		}
	>;
};

/**
 * [Dev Note] GraphQL can return a complex nested structure.
 * This helper flattens it to a simple object for easier form binding.
 *
 * @param data - Extracted payload from the GraphQL response.
 * @param fallbackError - Fallback error message if data is null/undefined or not an object.
 * @throws {Error} If data is not valid.
 * @returns Flattened object with values mapped directly to the fields.
 */
export function flattenGraphQLRecord<T>(
	data: any,
	fallbackError: string = "An unknown error occurred",
): T {
	if (!data || typeof data !== "object") {
		throw new Error(fallbackError);
	}

	return Object.fromEntries(
		Object.entries(data).map(([key, field]) => [
			key,
			field !== null && typeof field === "object" && "value" in field
				? (field as { value: unknown }).value
				: (field ?? null),
		]),
	) as T;
}
