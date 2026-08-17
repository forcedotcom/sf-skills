/**
 * Builds the CMS `managed_content { search { searchContentInChannels … } }`
 * fragment as a {@link QueryFragmentContribution} with `placement: "root"` — a
 * sibling of the `uiapi` block in the combined document.
 *
 * The `$cmsContentTypeFQNs` declaration, its `contentTypeFQNs:` argument, and
 * its variable value are all emitted only when a non-empty content-type list is
 * passed; on the bootstrap call (no types known) they are omitted entirely.
 */

import type { QueryFragmentContribution } from "../types";

export interface BuildCmsFragmentParams {
	/** Search keyword → `$cmsKeyword`. */
	keyword: string;
	/** UIBundle Id fed into the query → `$UIBundleId` (from `getUIBundleId()`). */
	uiBundleId: string;
	/** Pagination offset → `$cmsOffset` (already clamped `>= 0` by the caller). */
	offset: number;
	/** Page size → `$cmsLimit` (validated against `pageSizeOptions` upstream). */
	limit: number;
	/**
	 * Discovered/selected content-type FQNs → the schema's `contentTypeFQNs`
	 * argument (via `$cmsContentTypeFQNs`). When absent, null, or empty, those
	 * pieces are omitted entirely (bootstrap call). Callers pass ONLY
	 * `isValidCmsFqn`-validated values.
	 */
	contentTypes?: string[] | null;
}

/**
 * Builds the CMS fragment contribution. The content-type filter pieces are
 * included only when `params.contentTypes` is a non-empty array.
 */
export function buildCmsQueryFragment(params: BuildCmsFragmentParams): QueryFragmentContribution {
	const { keyword, uiBundleId, offset, limit, contentTypes } = params;

	const hasContentTypes = Array.isArray(contentTypes) && contentTypes.length > 0;

	const variableDeclarations = [
		"$cmsKeyword: String!",
		"$UIBundleId: ID!",
		"$cmsOffset: Int!",
		"$cmsLimit: Int!",
	];

	const variables: Record<string, unknown> = {
		cmsKeyword: keyword,
		UIBundleId: uiBundleId,
		cmsOffset: offset,
		cmsLimit: limit,
	};

	// CONDITIONAL: declare + pass + supply the content-type filter only when a
	// non-empty list is provided. Otherwise these three pieces are all absent.
	// The schema argument is `contentTypeFQNs` (a list of content-type FQNs) —
	// NOT `contentTypes`; the latter is rejected as an unknown field argument.
	const contentTypesArg = hasContentTypes ? "\n          contentTypeFQNs: $cmsContentTypeFQNs" : "";
	if (hasContentTypes) {
		variableDeclarations.push("$cmsContentTypeFQNs: [String!]");
		variables.cmsContentTypeFQNs = contentTypes;
	}

	const fragment = `managed_content {
  search {
    searchContentInChannels(
      searchIdentifiers: { uibundleIds: [$UIBundleId] }
      keyword: $cmsKeyword
      pagination: { limit: $cmsLimit, offset: $cmsOffset }${contentTypesArg}
    ) {
      total
      offset
      pageSize
      items {
        managedContentId
        managedContentKey
        title
        contentType
        language
        highlightedSnippet
        managedContentChannelDeliveryDetails {
          contentUrl
          publishedDate
          managedContentChannelDetails { id name type }
        }
      }
    }
  }
}`;

	return {
		variableDeclarations,
		variables,
		placement: "root",
		fragment,
	};
}
