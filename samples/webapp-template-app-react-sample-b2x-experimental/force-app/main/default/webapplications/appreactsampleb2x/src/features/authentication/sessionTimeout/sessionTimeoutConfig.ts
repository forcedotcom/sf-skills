/**
 * Configuration constants for session timeout monitoring
 */

// ============================================================================
// Retry Configuration
// ============================================================================

/** Initial delay for first retry attempt (2 seconds) */
export const INITIAL_RETRY_DELAY = 2000;

/** Maximum number of retry attempts before giving up */
export const MAX_RETRY_ATTEMPTS = 10;

/** Maximum retry delay (30 minutes) */
export const MAX_RETRY_DELAY = 30 * 60 * 1000;

// ============================================================================
// Session Storage Keys
// ============================================================================

/** sessionStorage keys used by session validator */
export const STORAGE_KEYS = {
	/** Flag to show session expired message on login page */
	SHOW_SESSION_MESSAGE: "lwrSessionValidator.showSessionMessage",
} as const;

// ============================================================================
// Servlet Configuration
// ============================================================================

/** SessionTimeServlet configuration */
export const SESSION_CONFIG = {
	/** Relative URL to SessionTimeServlet */
	SERVLET_URL: "/sfsites/c/_nc_external/system/security/session/SessionTimeServlet",

	/** Latency buffer to subtract from server response (seconds) */
	LATENCY_BUFFER_SECONDS: 3,

	/** CSRF protection prefix in servlet responses */
	CSRF_TOKEN: "while(1);\n",
} as const;

// ============================================================================
// UI Labels
// ============================================================================

/**
 * UI labels for session timeout components
 */
export const LABELS = {
	/** Title for session warning modal */
	sessionWarningTitle: "Session Timeout Warning",

	/** Message text in session warning modal */
	sessionWarningMessage:
		"For security, we log you out if you’re inactive for too long. To continue working, click Continue before the time expires.",

	/** Text for "Continue" button */
	continueButton: "Continue",

	/** Text for "Log Out" button */
	logoutButton: "Log Out",

	/** Message shown on login page after session expires */
	invalidSessionMessage: "Your session has expired. Please log in again.",

	/** Accessibility label for close button */
	closeLabel: "Close",
} as const;

// ============================================================================
// Session Timeout Configuration
// ============================================================================

/** Session warning time in seconds (30 seconds) */
export const SESSION_WARNING_TIME = 30;
