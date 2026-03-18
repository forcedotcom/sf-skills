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
 * @returns Parsed session response
 * @throws Error if response cannot be parsed
 */
function parseResponseResult(text: string): SessionResponse {
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
		throw new Error(
			`Failed to parse session response: ${error instanceof Error ? error.message : "Unknown error"}`,
		);
	}
}

/**
 * Call SessionTimeServlet API
 * Internal function used by both poll and extend functions
 *
 * @param basePath - Community base path (e.g., "/sfsites/c/")
 * @param extend - Whether to extend the session (updateTimedOutSession param)
 * @returns Session response with remaining time
 * @throws Error if API call fails or security checks fail
 */
async function callSessionTimeServlet(
	basePath: string,
	extend: boolean = false,
): Promise<SessionResponse> {
	// Build URL with cache-busting timestamp
	const timestamp = Date.now();
	let url = `${basePath}${SESSION_CONFIG.SERVLET_URL}?buster=${timestamp}`;

	if (extend) {
		url += "&updateTimedOutSession=true";
	}

	try {
		const response = await fetch(url, {
			method: "GET",
			credentials: "same-origin", // Include cookies for session
			cache: "no-cache",
			// Security headers
			headers: {
				"X-Requested-With": "XMLHttpRequest", // Helps identify XHR requests
			},
		});

		if (!response.ok) {
			// Provide more context for common error codes
			if (response.status === 401) {
				throw new Error("Session expired or unauthorized");
			} else if (response.status === 403) {
				throw new Error("Access forbidden");
			} else if (response.status === 404) {
				throw new Error("Session endpoint not found");
			} else {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}
		}

		// Security: Validate content type (should be text or JSON)
		const contentType = response.headers.get("content-type");
		if (contentType && !contentType.includes("text") && !contentType.includes("json")) {
			throw new Error(`Unexpected content type: ${contentType}`);
		}

		const text = await response.text();
		const parsed = parseResponseResult(text);

		// Apply latency buffer to account for network delay
		const adjustedSecondsRemaining = Math.max(0, parsed.sr - SESSION_CONFIG.LATENCY_BUFFER_SECONDS);

		return {
			sp: parsed.sp,
			sr: adjustedSecondsRemaining,
		};
	} catch (error) {
		// Don't log the full URL in production to avoid leaking sensitive info
		console.error("[sessionTimeService] API call failed:", error);
		throw error;
	}
}

/**
 * Poll SessionTimeServlet to check remaining session time
 * Called periodically to monitor session status
 *
 * @param basePath - Community base path (e.g., "/sfsites/c/")
 * @returns Session response with remaining time (after latency buffer adjustment)
 * @throws Error if API call fails
 *
 * @example
 * const { sr, sp } = await pollSessionTimeServlet('/sfsites/c/');
 * if (sr <= 300) {
 *   // Less than 5 minutes remaining
 *   showWarning();
 * }
 */
export async function pollSessionTimeServlet(basePath: string): Promise<SessionResponse> {
	return callSessionTimeServlet(basePath, false);
}

/**
 * Extend the current session time
 * Called when user clicks "Continue Working" in warning modal
 *
 * @param basePath - Community base path (e.g., "/sfsites/c/")
 * @returns Session response with new remaining time
 * @throws Error if API call fails
 *
 * @example
 * const { sr } = await extendSessionTime('/sfsites/c/');
 * console.log(`Session extended. ${sr} seconds remaining.`);
 */
export async function extendSessionTime(basePath: string): Promise<SessionResponse> {
	return callSessionTimeServlet(basePath, true);
}

/**
 * Export parseResponseResult for testing purposes
 * @internal
 */
export { parseResponseResult };
