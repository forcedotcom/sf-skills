import { geocodeAddress, getStateZipFromAddress, type GeocodeResult } from "@/utils/geocode";
import { useCachedAsyncData } from "@/features/object-search/hooks/useCachedAsyncData";

async function geocodeWithFallback(address: string): Promise<GeocodeResult | null> {
	const normalized = address.replace(/\n/g, ", ").trim();
	const result = await geocodeAddress(normalized);
	if (result != null) return result;

	// Fallback: try state + zip if full address failed
	const stateZip = getStateZipFromAddress(normalized);
	if (stateZip !== normalized) {
		return geocodeAddress(stateZip);
	}
	return null;
}

export function useGeocode(address: string | null | undefined): {
	coords: GeocodeResult | null;
	loading: boolean;
} {
	const trimmed = address?.trim() ?? "";

	const { data: coords, loading } = useCachedAsyncData(
		() => {
			if (!trimmed) return Promise.resolve(null);
			return geocodeWithFallback(trimmed);
		},
		[trimmed],
		{ key: `geocode:${trimmed}`, ttl: 600_000 },
	);

	return { coords, loading };
}
