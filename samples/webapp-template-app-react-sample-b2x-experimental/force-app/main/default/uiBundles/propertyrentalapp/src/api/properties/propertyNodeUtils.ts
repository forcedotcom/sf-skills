import type { PropertySearchNode } from "./propertySearchService";

const AMENITIES_SEPARATOR = " | ";

/** Pick the primary (or first available) image URL from the child images. */
export function extractPrimaryImageUrl(node: PropertySearchNode): string | null {
	const images = (node.Property_Images__r?.edges ?? []).flatMap((e) => (e?.node ? [e.node] : []));
	if (images.length === 0) return null;
	const primary =
		images.find((i) => (i.Image_Type__c?.value ?? "").toLowerCase() === "primary") ??
		images.find((i) => Boolean(i.Image_URL__c?.value));
	return primary?.Image_URL__c?.value ?? null;
}

/** Join feature descriptions into a single amenities string. */
export function extractAmenities(node: PropertySearchNode): string {
	const features = (node.Property_Features__r?.edges ?? []).flatMap((e) =>
		e?.node ? [e.node] : [],
	);
	return features
		.map((f) => f.Description__c?.value)
		.filter((d): d is string => d != null && d.trim() !== "")
		.join(AMENITIES_SEPARATOR);
}

/** Extract the address string from a property node. */
export function extractAddress(node: PropertySearchNode): string | null {
	return node.Address__c?.value ?? node.Address__c?.displayValue ?? null;
}
