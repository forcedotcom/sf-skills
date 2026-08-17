import { getCurrentApp } from "@salesforce/platform-sdk";

/** Returns the UIBundle id for CMS search, resolved from the running app. */
export async function getUIBundleId(): Promise<string> {
	const app = await getCurrentApp();
	return app.identity?.bundleId ?? "";
}

/** Shape guard for a UIBundle record id (9YE + 12-15 alphanumerics). */
export const UI_BUNDLE_ID_PATTERN = /^9YE[a-zA-Z0-9]{12,15}$/;

/** True when `id` is a well-formed (9YE-shaped) UIBundle id. */
export function isConfiguredUIBundleId(id: string): boolean {
	return UI_BUNDLE_ID_PATTERN.test(id.trim());
}
