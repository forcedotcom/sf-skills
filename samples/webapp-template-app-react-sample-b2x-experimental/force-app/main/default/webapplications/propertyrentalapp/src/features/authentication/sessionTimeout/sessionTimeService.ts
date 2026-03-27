/**
 * SessionTimeServlet API service
 * Handles communication with the session validation endpoint
 */

import { SESSION_CONFIG } from "./sessionTimeoutConfig";

/**
 * Response from SessionTimeServlet API
 */
export interface SessionResponse {
	/** Session phase */
	sp: number;
	/** Seconds remaining in session */
	sr: number;
}

/**
 * Parse the servlet response text into SessionResponse object
 * Handles CSRF protection prefix
 *
 * @param text - Raw response text from servlet
 * @returns Parsed session response, or undefined if parsing fails
 */
function parseResponseResult(text: string): SessionResponse | undefined {
	let cleanedText = text;

	// Strip CSRF protection prefix if present
	if (cleanedText.startsWith(SESSION_CONFIG.CSRF_TOKEN)) {
		cleanedText = cleanedText.substring(SESSION_CONFIG.CSRF_TOKEN.length);
	}

	// Trim whitespace
	cleanedText = cleanedText.trim();

	try {
		const parsed = JSON.parse(cleanedText) as SessionResponse;

		// Validate response structure
		if (typeof parsed.sp !== "number" || typeof parsed.sr !== "number") {
			throw new Error("Invalid response structure: missing sp or sr properties");
		}

		return parsed;
	} catch (error) {
		console.error("[sessionTimeService] Failed to parse response:", error, "Text:", cleanedText);
	}
}

/**
 * Call SessionTimeServlet API
 * Internal function used by both poll and extend functions.
 * Returns undefined on any failure so the session timeout feature
 * never crashes the running application.
 *
 * @param basePath - Community base path (e.g., "/sfsites/c/")
 * @param extend - Whether to extend the session (updateTimedOutSession param)
 * @returns Session response with remaining time, or undefined on failure
 */
async function callSessionTimeServlet(
	basePath: string,
	extend: boolean = false,
): Promise<SessionResponse | undefined> {
	// Build URL with cache-busting timestamp
	const timestamp = Date.now();
	let url = `${basePath}${SESSION_CONFIG.SERVLET_URL}?buster=${timestamp}`;

	if (extend) {
		url += "&updateTimedOutSession=true";
	}

	try {
		const response = await fetch(url, {
			method: "GET",
			credentials: "same-origin",
			cache: "no-cache",
			headers: {
				"X-Requested-With": "XMLHttpRequest",
			},
		});

		if (!response.ok) {
			console.error(`[sessionTimeService] HTTP ${response.status}: ${response.statusText}`);
			return undefined;
		}

		const contentType = response.headers.get("content-type");
		if (contentType && !contentType.includes("text") && !contentType.includes("json")) {
			console.error(`[sessionTimeService] Unexpected content type: ${contentType}`);
			return undefined;
		}

		const text = await response.text();
		const parsed = parseResponseResult(text);
		if (!parsed) {
			return undefined;
		}

		return {
			sp: parsed.sp,
			sr: Math.max(0, parsed.sr - SESSION_CONFIG.LATENCY_BUFFER_SECONDS),
		};
	} catch (error) {
		console.error("[sessionTimeService] API call failed:", error);
		return undefined;
	}
}

/**
 * Poll SessionTimeServlet to check remaining session time
 * Called periodically to monitor session status
 *
 * @param basePath - Community base path (e.g., "/sfsites/c/")
 * @returns Session response with remaining time, or undefined on failure
 *
 * @example
 * const response = await pollSessionTimeServlet('/sfsites/c/');
 * if (response && response.sr <= 300) {
 *   showWarning();
 * }
 */
export async function pollSessionTimeServlet(
	basePath: string,
): Promise<SessionResponse | undefined> {
	return callSessionTimeServlet(basePath, false);
}

/**
 * Extend the current session time
 * Called when user clicks "Continue Working" in warning modal
 *
 * @param basePath - Community base path (e.g., "/sfsites/c/")
 * @returns Session response with new remaining time, or undefined on failure
 *
 * @example
 * const response = await extendSessionTime('/sfsites/c/');
 * if (response) {
 *   console.log(`Session extended. ${response.sr} seconds remaining.`);
 * }
 */
export async function extendSessionTime(basePath: string): Promise<SessionResponse | undefined> {
	return callSessionTimeServlet(basePath, true);
}

/**
 * Export parseResponseResult for testing purposes
 * @internal
 */
export { parseResponseResult };
