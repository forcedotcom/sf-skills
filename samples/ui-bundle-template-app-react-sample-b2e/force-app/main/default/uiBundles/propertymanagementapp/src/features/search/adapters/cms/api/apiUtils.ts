/**
 * Self-contained CMS Connect REST helpers (URL builder + authenticated GET).
 */

import { createDataSDK } from "@salesforce/platform-sdk";

// The build injects the org's API version via `__SF_API_VERSION__`; the literal
// is only a fallback for environments (e.g. unit tests) where it is undefined.
declare const __SF_API_VERSION__: string;

/** Project-standard API version, mirroring `@salesforce/ui-bundle/api`'s clients. */
const API_VERSION: string = typeof __SF_API_VERSION__ !== "undefined" ? __SF_API_VERSION__ : "65.0";

/**
 * The bundle's build-time API version as a number (e.g. `68.0`), i.e. the
 * version the SDK's GraphQL/REST requests are actually issued at. `0` when it
 * cannot be parsed. Distinct from the org's advertised max version.
 */
export function getBuildApiVersion(): number {
	const v = Number.parseFloat(API_VERSION);
	return Number.isFinite(v) ? v : 0;
}

/**
 * Percent-encodes a single path segment (SSRF / path-injection guard). Mirrors
 * the reference `safeEncodePath`.
 */
export function safeEncodePath(segment: string): string {
	return encodeURIComponent(segment);
}

/** Builds an absolute Connect REST URL from a version-relative sub-path. */
export function connectUrl(subPath: string): string {
	const normalized = subPath.startsWith("/") ? subPath : `/${subPath}`;
	return `/services/data/v${API_VERSION}/connect${normalized}`;
}

/**
 * GETs a Connect JSON resource via the platform SDK's authenticated `fetch`
 * and returns the parsed body. Throws on SDK-init failure or a non-OK response
 * (the caller decides how a whole-request failure surfaces).
 */
export async function connectGetJson<T = unknown>(url: string): Promise<T> {
	const sdk = await createDataSDK();
	if (!sdk?.fetch) {
		throw new Error("Failed to initialize data SDK for CMS REST call");
	}
	const response = await sdk.fetch(url, {
		method: "GET",
		headers: { Accept: "application/json" },
	});
	if (!response.ok) {
		throw new Error(`CMS REST request failed: ${response.status} ${response.statusText}`);
	}
	return (await response.json()) as T;
}
