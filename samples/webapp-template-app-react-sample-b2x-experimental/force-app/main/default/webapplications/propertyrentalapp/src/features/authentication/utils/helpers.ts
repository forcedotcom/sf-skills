/**
 * MAINTAINABILITY: Robust error extraction.
 * Handles strings, objects, and standard Error instances.
 *
 * @param err - The error object (unknown type)
 * @param fallback - Fallback message if error doesn't have a message property
 * @returns The error message string
 */
export function getErrorMessage(err: unknown, fallback: string): string {
	if (err instanceof Error) return err.message;
	if (typeof err === "string") return err;
	// Check if it's an object with a message property
	if (typeof err === "object" && err !== null && "message" in err) {
		return String((err as { message: unknown }).message);
	}
	return fallback;
}

/**
 * [Dev Note] Helper to parse the fetch Response.
 * It handles the distinction between success (JSON) and failure (throwing Error).
 */
export async function handleApiResponse<T = unknown>(
	response: Response,
	fallbackError: string,
): Promise<T> {
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
		// [Dev Note] Throwing here allows the calling component to catch and
		// display the error via getErrorMessage()
		throw new Error(parseApiResponseError(data, fallbackError));
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

/**
 * [Dev Note] Salesforce APIs may return errors as an array or a single object.
 * This helper standardizes the extraction of the error message string.
 *
 * @param data - The response data.
 * @param fallbackError - Fallback error message if response doesn't have a message property
 * @returns The error message string
 */
function parseApiResponseError(
	data: any,
	fallbackError: string = "An unknown error occurred",
): string {
	if (data?.message) {
		return data.message;
	}
	if (data?.error) {
		return data.error;
	}
	if (data?.errors && Array.isArray(data.errors) && data.errors.length > 0) {
		return data.errors.join(" ") || fallbackError;
	}
	if (Array.isArray(data) && data.length > 0) {
		return (
			data
				.map((e) => e?.message)
				.filter(Boolean)
				.join(" ") || fallbackError
		);
	}
	return fallbackError;
}
