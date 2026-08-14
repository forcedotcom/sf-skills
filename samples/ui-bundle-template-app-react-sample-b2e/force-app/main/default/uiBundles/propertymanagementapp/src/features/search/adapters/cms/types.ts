/**
 * CMS source config + the response shapes returned by
 * `managed_content.search.searchContentInChannels`.
 */

export interface CmsChannelDetails {
	id: string;
	name: string;
	type?: string;
}

export interface CmsChannelDeliveryDetails {
	contentUrl?: string;
	publishedDate?: string;
	managedContentChannelDetails: CmsChannelDetails;
}

export interface CmsSearchItem {
	managedContentId: string;
	managedContentKey: string;
	title: string;
	contentType: string;
	language?: string;
	highlightedSnippet?: string;
	managedContentChannelDeliveryDetails: CmsChannelDeliveryDetails[];
}

export interface CmsSearchResponse {
	total: number;
	offset: number;
	pageSize: number;
	items: CmsSearchItem[];
}

/**
 * Configuration for one CMS source in a search experience.
 *
 * Deliberately minimal — unlike an SObject source (which hardcodes an object
 * name, searchable/display fields, filters, etc.), a CMS source hardcodes
 * nothing about the CMS data. The search channel id comes from
 * `searchChannel.getUIBundleId()`; content types are discovered at runtime from
 * the search results. This config only names the source and (optionally)
 * describes how to build a result link.
 */
export interface CmsSourceConfig {
	/** Discriminator — selects the CMS runtime adapter. */
	kind: "cms";
	/**
	 * Stable identifier. Used as the scope key, the result-map key, and the
	 * prefix for CMS content-type scope entries (`"<key>:<fqn>"`). Must match
	 * `/^[A-Za-z_][A-Za-z0-9_]*$/`.
	 */
	key: string;
	/** Plural display label — dropdown entry + section header, e.g. "Content". */
	label: string;
	/** Singular label for the per-card source badge. Falls back to `label`. */
	labelSingular?: string;
	/**
	 * Optional URL pattern used by `CmsResultRow` to build a result link.
	 * Tokens: `:id` (managedContentId), `:key` (managedContentKey),
	 * `:contentType` (contentType). When omitted, the row falls back to
	 * `/content/:contentType/:id`.
	 */
	routePattern?: string;
	// NO channelId, NO content types, NO displayFields — all resolved at runtime.
}
