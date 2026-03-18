import { AUTH_REDIRECT_PARAM } from "./authenticationConfig";
import { z } from "zod";

/** Email field validation */
export const emailSchema = z.string().trim().email("Please enter a valid email address");

/** Password field validation (minimum 8 characters) */
export const passwordSchema = z.string().min(8, "Password must be at least 8 characters");

/**
 * Shared schema for new password + confirmation fields.
 * Validates password length and matching confirmation.
 */
export const newPasswordSchema = z
	.object({
		newPassword: passwordSchema,
		confirmPassword: z.string().min(1, "Please confirm your password"),
	})
	.refine((data) => data.newPassword === data.confirmPassword, {
		message: "Passwords do not match",
		path: ["confirmPassword"],
	});

/**
 *
 * Extracts the startUrl from URLSearchParams, defaulting to '/'.
 *
 * SECURITY NOTE: This function strictly validates the URL to prevent
 * Open Redirect vulnerabilities. It allows only relative paths.
 *
 * @param searchParams - The URLSearchParams object from useSearchParams()
 * @returns The start URL for post-authentication redirect
 */
export function getStartUrl(searchParams: URLSearchParams): string {
	// 1. Check for the standard redirect parameter
	const url = searchParams.get(AUTH_REDIRECT_PARAM);
	// 2. Security Check: Validation Logic
	if (url && isValidRedirect(url)) {
		return url;
	}
	// 3. Fallback: Default to root
	return "/";
}

/**
 * [Dev Note] Security: Validates that the redirect URL is a relative path
 * to prevent Open Redirect vulnerabilities.
 *
 * Security Checks:
 * 1. Rejects protocol-relative URLs (//)
 * 2. Rejects backslash usage which some browsers treat as slashes (/\)
 * 3. Rejects control characters
 */
function isValidRedirect(url: string): boolean {
	// Basic structure check
	if (!url.startsWith("/") || url.startsWith("//")) return false;
	// Security: Reject backslashes to prevent /\example.com bypasses
	if (url.includes("\\")) return false;
	// Robustness: Ensure it doesn't contain whitespace/control characters
	if (/[^\u0021-\u00ff]/.test(url)) return false;
	return true;
}

/**
 * Shared response type for authentication endpoints (login/register).
 * Success responses contain `success: true` and `redirectUrl`.
 * Error responses contain `errors` array.
 */
export interface AuthResponse {
	success?: boolean;
	redirectUrl?: string | null;
	errors?: string[];
}
