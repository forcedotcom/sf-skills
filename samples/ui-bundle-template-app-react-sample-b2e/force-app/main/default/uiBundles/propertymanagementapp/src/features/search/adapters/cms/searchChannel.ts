import { createDataSDK, getCurrentApp } from "@salesforce/platform-sdk";
import { fetchI18nContext } from "@salesforce/platform-sdk/i18n";

/** Returns the UIBundle id for CMS search, resolved from the running app. */
export async function getUIBundleId(): Promise<string> {
	const app = await getCurrentApp();
	return app.identity?.bundleId ?? "";
}

/** Fallback language tag used when the user's own language can't be resolved. */
export const DEFAULT_LANGUAGE = "en-US";

/** Returns the current user's language tag (e.g. `"en-US"`), falling back to {@link DEFAULT_LANGUAGE}. */
export async function getUserLanguage(): Promise<string> {
	try {
		const sdk = await createDataSDK();
		if (!sdk?.graphql) return DEFAULT_LANGUAGE;
		const ctx = await fetchI18nContext(sdk);
		return ctx.lang || DEFAULT_LANGUAGE;
	} catch {
		return DEFAULT_LANGUAGE;
	}
}

/** Shape guard for a UIBundle record id (9YE + 12-15 alphanumerics). */
export const UI_BUNDLE_ID_PATTERN = /^9YE[a-zA-Z0-9]{12,15}$/;

/** True when `id` is a well-formed (9YE-shaped) UIBundle id. */
export function isConfiguredUIBundleId(id: string): boolean {
	return UI_BUNDLE_ID_PATTERN.test(id.trim());
}
