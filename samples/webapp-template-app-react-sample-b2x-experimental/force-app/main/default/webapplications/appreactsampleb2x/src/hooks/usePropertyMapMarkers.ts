/**
 * Fetches property addresses for the current page of results only, geocodes them in parallel,
 * and returns map markers (one pin per property in the current window).
 */
import { useState, useEffect } from "react";
import { fetchPropertyAddresses } from "@/api/properties/propertyDetailGraphQL";
import { geocodeAddress, getStateZipFromAddress } from "@/utils/geocode";
import { getPropertyIdFromRecord } from "@/hooks/usePropertyPrimaryImages";
import type { SearchResultRecord } from "@/types/searchResults.js";
import type { MapMarker } from "@/components/properties/PropertyMap";

function getListingName(record: {
	fields?: Record<string, { value?: unknown; displayValue?: string | null }>;
}): string {
	const f = record.fields?.Name;
	if (!f || typeof f !== "object") return "Property";
	if (f.displayValue != null && f.displayValue !== "") return String(f.displayValue);
	if (f.value != null && typeof f.value === "string") return f.value;
	return "Property";
}

/** Round to 5 decimals (~1 m) so near-duplicate coords group together */
function key(lat: number, lng: number): string {
	return `${lat.toFixed(5)},${lng.toFixed(5)}`;
}

/**
 * When multiple markers share the same lat/lng, offset them in a small circle so they appear
 * close together but are all visible (no stacking).
 */
function spreadDuplicateMarkers(markers: MapMarker[]): MapMarker[] {
	const groups = new Map<string, MapMarker[]>();
	for (const m of markers) {
		const k = key(m.lat, m.lng);
		if (!groups.has(k)) groups.set(k, []);
		groups.get(k)!.push(m);
	}
	const result: MapMarker[] = [];
	const radiusDeg = 0.0004; // ~40–50 m so pins sit close but visible
	for (const group of groups.values()) {
		if (group.length === 1) {
			result.push(group[0]);
			continue;
		}
		for (let i = 0; i < group.length; i++) {
			const m = group[i];
			const angle = (i / group.length) * 2 * Math.PI;
			result.push({
				...m,
				lat: m.lat + radiusDeg * Math.cos(angle),
				lng: m.lng + radiusDeg * Math.sin(angle),
			});
		}
	}
	return result;
}

export function usePropertyMapMarkers(results: SearchResultRecord[]): {
	markers: MapMarker[];
	loading: boolean;
} {
	const [markers, setMarkers] = useState<MapMarker[]>([]);
	const [loading, setLoading] = useState(false);

	// Only the current page / current window of results
	const propertyIds = results
		.map((r) => r?.record && getPropertyIdFromRecord(r.record))
		.filter((id): id is string => Boolean(id));
	const propertyIdToLabel = new Map<string, string>();
	for (const r of results) {
		if (!r?.record) continue;
		const id = getPropertyIdFromRecord(r.record);
		if (id && !propertyIdToLabel.has(id)) {
			propertyIdToLabel.set(id, getListingName(r.record));
		}
	}

	useEffect(() => {
		if (propertyIds.length === 0) {
			setMarkers([]);
			setLoading(false);
			return;
		}
		let cancelled = false;
		setLoading(true);
		const uniqIds = [...new Set(propertyIds)];
		fetchPropertyAddresses(uniqIds)
			.then((idToAddress) => {
				if (cancelled) return;
				const toGeocode = Object.entries(idToAddress).filter(
					([, addr]) => addr != null && addr.trim() !== "",
				);
				if (toGeocode.length === 0) {
					setMarkers([]);
					setLoading(false);
					return;
				}
				// Geocode all addresses in parallel; fallback to City, State Zip if full address fails
				Promise.all(
					toGeocode.map(async ([id, address]) => {
						const normalized = address.replace(/\n/g, ", ").trim();
						let coords = await geocodeAddress(normalized);
						if (!coords) {
							const stateZip = getStateZipFromAddress(normalized);
							if (stateZip !== normalized) {
								coords = await geocodeAddress(stateZip);
							}
						}
						return coords ? { id, coords } : null;
					}),
				)
					.then((resolved) => {
						if (cancelled) return;
						const raw: MapMarker[] = resolved
							.filter((r): r is { id: string; coords: { lat: number; lng: number } } => r != null)
							.map(({ id, coords }) => ({
								lat: coords.lat,
								lng: coords.lng,
								label: propertyIdToLabel.get(id) ?? "Property",
								propertyId: id,
							}));
						setMarkers(spreadDuplicateMarkers(raw));
					})
					.catch(() => {
						if (!cancelled) setMarkers([]);
					})
					.finally(() => {
						if (!cancelled) setLoading(false);
					});
			})
			.catch(() => {
				if (!cancelled) {
					setMarkers([]);
					setLoading(false);
				}
			});
		return () => {
			cancelled = true;
		};
	}, [propertyIds.join(",")]);

	return { markers, loading };
}
