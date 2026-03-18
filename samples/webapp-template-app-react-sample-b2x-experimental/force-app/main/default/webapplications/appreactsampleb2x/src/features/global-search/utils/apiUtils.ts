/**
 * API Utilities
 *
 * Generic utility functions for API requests, validation, and URL handling.
 */

import type { ZodSchema } from "zod";

export interface FetchAndValidateOptions<T> {
	schema: ZodSchema<T>;
	errorContext: string;
	extractData?: (data: unknown) => unknown;
}

export async function fetchAndValidate<T>(
	fetchFn: () => Promise<Response>,
	options: FetchAndValidateOptions<T>,
): Promise<T> {
	const { schema, errorContext, extractData } = options;

	try {
		const response = await fetchFn();

		if (!response.ok) {
			throw new Error(`Failed to fetch ${errorContext}: ${response.status} ${response.statusText}`);
		}

		const data = await response.json();
		const dataToValidate = extractData ? extractData(data) : data;
		const validationResult = schema.safeParse(dataToValidate);

		if (!validationResult.success) {
			throw new Error(`Invalid ${errorContext} response format: ${validationResult.error.message}`);
		}

		return validationResult.data;
	} catch (error) {
		if (error instanceof Error && error.name === "ZodError") {
			throw new Error(`Invalid ${errorContext} response format: ${error.message}`);
		}

		if (
			error instanceof Error &&
			(error.message.includes("Failed to fetch") || error.message.includes("Invalid"))
		) {
			throw error;
		}

		throw new Error(
			`Error fetching ${errorContext}: ${
				error instanceof Error ? error.message : (error?.toString() ?? "Unknown error")
			}`,
		);
	}
}

export function safeEncodePath(segment: string): string {
	return encodeURIComponent(segment);
}
