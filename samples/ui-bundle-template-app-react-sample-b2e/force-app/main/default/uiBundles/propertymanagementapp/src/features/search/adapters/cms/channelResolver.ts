/**
 * Extracts the CMS channel id from a search result so it can feed the
 * searchable-content-types Connect endpoint. There is one CMS channel for the
 * app, so any result carries it:
 *
 *   nodes[0].managedContentChannelDeliveryDetails[0].managedContentChannelDetails.id
 *
 * Returns `null` when any hop is missing (empty nodes, missing delivery
 * details, missing channel details / id) — the caller simply skips discovery.
 */

import type { SourceResult } from "../../types";
import type { CmsSearchResponse, CmsSearchItem } from "./types";

/** Accepts either a normalised `SourceResult` or a raw `CmsSearchResponse`. */
type ChannelSource = SourceResult | CmsSearchResponse | null | undefined;

function getNodes(result: ChannelSource): unknown[] {
	if (!result) return [];
	// SourceResult carries `nodes`; CmsSearchResponse carries `items`.
	if ("nodes" in result && Array.isArray(result.nodes)) return result.nodes;
	if ("items" in result && Array.isArray(result.items)) return result.items;
	return [];
}

/**
 * Returns the channel id derived from the first result's delivery details, or
 * `null` when any level is absent. Validate the returned id's shape before it
 * enters a REST path (the discovery service does this).
 */
export function resolveChannelId(result: ChannelSource): string | null {
	const nodes = getNodes(result);
	const first = nodes[0] as Partial<CmsSearchItem> | undefined;
	if (!first) return null;

	const delivery = first.managedContentChannelDeliveryDetails?.[0];
	const id = delivery?.managedContentChannelDetails?.id;

	return typeof id === "string" && id.length > 0 ? id : null;
}
