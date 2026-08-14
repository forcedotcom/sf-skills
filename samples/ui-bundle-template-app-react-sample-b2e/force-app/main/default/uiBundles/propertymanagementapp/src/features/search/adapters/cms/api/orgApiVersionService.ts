/** Service to gate CMS search on the bundle's build-time API version. */

import { getBuildApiVersion } from "./apiUtils";

/** Minimum API version that supports CMS search. */
export const MIN_CMS_API_VERSION = 68;

/**
 * Whether CMS search can run — the synchronous core of the gate. Gated on the
 * bundle's build-time API version (`__SF_API_VERSION__`, injected from the
 * resolved org's API version at build time) being >= {@link MIN_CMS_API_VERSION}.
 *
 * The build version is the version every SDK GraphQL/REST request is actually
 * issued at, so it already reflects a concrete, org-supported API version: a
 * bundle built against an org resolves that org's max version, and a bundle
 * built below v68 sends its CMS query to `/services/data/v67.0/graphql` where
 * the v68 CMS backend is unavailable. Gating on the build version alone is
 * therefore both necessary and sufficient — and, unlike a runtime probe of the
 * bare `/services/data/` version-listing endpoint (which is not routed on guest
 * Experience Sites and would fail-close there), it works on every surface.
 *
 * Because it reads only the baked build version, it is safe to call during
 * render — e.g. to hide the CMS source's scope entry and result section when
 * the backend isn't available (see `ScopeSelector` and `SearchResults`).
 */
export function isCmsSearchSupported(): boolean {
	return getBuildApiVersion() >= MIN_CMS_API_VERSION;
}

/**
 * Resolves whether CMS search can run. Thin async wrapper over
 * {@link isCmsSearchSupported} that preserves the existing fetch-path call-site
 * contract (the fetch effect awaits it alongside the async UIBundle-id lookup).
 */
export function getOrgSupportsCmsSearch(): Promise<boolean> {
	return Promise.resolve(isCmsSearchSupported());
}
