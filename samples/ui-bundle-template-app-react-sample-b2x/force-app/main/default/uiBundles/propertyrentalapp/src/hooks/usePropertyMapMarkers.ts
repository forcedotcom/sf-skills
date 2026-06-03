/**
 * Builds map markers from search result nodes. Uses coordinates when available,
 * falls back to geocoding addresses for properties missing coordinates.
 */
import { useState, useEffect, useRef } from "react";
import { fetchPropertyAddresses } from "@/api/properties/propertyDetailGraphQL";
import { geocodeAddress, getStateZipFromAddress } from "@/utils/geocode";
import type { PropertySearchNode } from "@/api/properties/propertySearchService";
import type { MapMarker } from "@/components/properties/PropertyMap";

function getListingName(node: PropertySearchNode): string {
	if (node.Name?.displayValue != null && node.Name.displayValue !== "")
		return node.Name.displayValue;
	if (node.Name?.value != null && node.Name.value !== "") return node.Name.value;
	return "Property";
}

function toFiniteNumber(value: unknown): number | null {
	if (typeof value === "number" && Number.isFinite(value)) return value;
	if (typeof value === "string" && value.trim() !== "") {
		const n = Number(value);
		return Number.isFinite(n) ? n : null;
	}
	return null;
}

function getCoordinatesFromNode(node: PropertySearchNode): { lat: number; lng: number } | null {
	const lat = toFiniteNumber(node.Coordinates__Latitude__s?.value);
	const lng = toFiniteNumber(node.Coordinates__Longitude__s?.value);
	if (lat == null || lng == null) return null;
	return { lat, lng };
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

export function usePropertyMapMarkers(results: PropertySearchNode[]): {
	markers: MapMarker[];
	loading: boolean;
} {
	const [markers, setMarkers] = useState<MapMarker[]>([]);
	const [loading, setLoading] = useState(false);

	const propertyIds = results.map((r) => r.Id).filter(Boolean);
	const propertyIdToLabel = new Map<string, string>();
	for (const node of results) {
		if (!propertyIdToLabel.has(node.Id)) {
			propertyIdToLabel.set(node.Id, getListingName(node));
		}
	}
	const idsKey = [...new Set(propertyIds)].join(",");
	const uniqIds = idsKey === "" ? [] : idsKey.split(",");

	// Compute direct markers synchronously (nodes that already have coordinates)
	const directMarkers: MapMarker[] = [];
	const missingIds: string[] = [];
	for (const node of results) {
		if (!uniqIds.includes(node.Id)) continue;
		const coords = getCoordinatesFromNode(node);
		if (coords) {
			directMarkers.push({
				lat: coords.lat,
				lng: coords.lng,
				label: propertyIdToLabel.get(node.Id) ?? "Property",
				propertyId: node.Id,
			});
		}
	}
	for (const id of uniqIds) {
		const hasDirect = directMarkers.some((m) => m.propertyId === id);
		if (!hasDirect) missingIds.push(id);
	}

	// Handle cases that don't need async work during render
	const [prevIdsKey, setPrevIdsKey] = useState(idsKey);
	if (prevIdsKey !== idsKey) {
		setPrevIdsKey(idsKey);
		if (uniqIds.length === 0) {
			if (markers.length > 0) setMarkers([]);
			if (loading) setLoading(false);
		} else if (missingIds.length === 0) {
			setMarkers(spreadDuplicateMarkers(directMarkers));
			if (loading) setLoading(false);
		} else {
			if (!loading) setLoading(true);
		}
	}

	// Stable reference to labels for use in the async effect
	const labelMapRef = useRef(propertyIdToLabel);
	useEffect(() => {
		labelMapRef.current = propertyIdToLabel;
	});

	useEffect(() => {
		if (uniqIds.length === 0 || missingIds.length === 0) return;
		let cancelled = false;
		const currentLabels = labelMapRef.current;
		fetchPropertyAddresses(missingIds)
			.then((idToAddress) => {
				if (cancelled) return;
				const toGeocode = Object.entries(idToAddress).filter(
					([, addr]) => addr != null && addr.trim() !== "",
				);
				if (toGeocode.length === 0) {
					if (!cancelled) {
						setMarkers(spreadDuplicateMarkers(directMarkers));
						setLoading(false);
					}
					return;
				}
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
						const geocoded: MapMarker[] = resolved
							.filter((r): r is { id: string; coords: { lat: number; lng: number } } => r != null)
							.map(({ id, coords }) => ({
								lat: coords.lat,
								lng: coords.lng,
								label: currentLabels.get(id) ?? "Property",
								propertyId: id,
							}));
						setMarkers(spreadDuplicateMarkers([...directMarkers, ...geocoded]));
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
		// eslint-disable-next-line react-hooks/exhaustive-deps --- only re-run when IDs change
	}, [idsKey]);

	return { markers, loading };
}
