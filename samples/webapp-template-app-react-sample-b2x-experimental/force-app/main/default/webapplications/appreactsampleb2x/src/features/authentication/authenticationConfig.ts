/**
 * [Dev Note] Centralized configuration for Auth routes.
 * Each route contains both the path and page title.
 * Using constants prevents typos in route paths across the application.
 */
export const ROUTES = {
	LOGIN: {
		PATH: "/login",
		TITLE: "Login | MyApp",
	},
	REGISTER: {
		PATH: "/register",
		TITLE: "Create Account | MyApp",
	},
	FORGOT_PASSWORD: {
		PATH: "/forgot-password",
		TITLE: "Recover Password | MyApp",
	},
	RESET_PASSWORD: {
		PATH: "/reset-password",
		TITLE: "Reset Password | MyApp",
	},
	PROFILE: {
		PATH: "/profile",
		TITLE: "My Profile | MyApp",
	},
	CHANGE_PASSWORD: {
		PATH: "/change-password",
		TITLE: "Change Password | MyApp",
	},
} as const;

/**
 * [Dev Note] Centralized configuration for API endpoints.
 * These are server-side endpoints, not client-side routes.
 */
export const API_ROUTES = {
	// W-21253864: Logout URL integration is not currently supported
	LOGOUT: "/secur/logout.jsp",
} as const;

/**
 * [Dev Note] Query parameter key used to store the return URL.
 * e.g. /login?startUrl=/profile
 */
export const AUTH_REDIRECT_PARAM = "startUrl";

/**
 * Placeholder text constants for authentication form inputs.
 */
export const AUTH_PLACEHOLDERS = {
	EMAIL: "asalesforce@example.com",
	PASSWORD: "",
	PASSWORD_CREATE: "",
	PASSWORD_CONFIRM: "",
	PASSWORD_NEW: "",
	PASSWORD_NEW_CONFIRM: "",
	FIRST_NAME: "Astro",
	LAST_NAME: "Salesforce",
	USERNAME: "asalesforce",
} as const;
