/**
 * Geocode an address to lat/lng using OpenStreetMap Nominatim (free, no API key).
 * Results are cached in memory (including 200 responses with empty results).
 * Allows limited parallel in-flight requests (maxConcurrent).
 */

const CACHED_EMPTY = Symbol("cached empty geocode");
type CacheEntry = { lat: number; lng: number } | typeof CACHED_EMPTY;

const CACHE = new Map<string, CacheEntry>();
const MAX_CONCURRENT = 6;
let inFlight = 0;
const queue: Array<() => void> = [];

function acquire(): Promise<void> {
	if (inFlight < MAX_CONCURRENT) {
		inFlight += 1;
		return Promise.resolve();
	}
	return new Promise<void>((resolve) => {
		queue.push(() => {
			inFlight += 1;
			resolve();
		});
	});
}

function release(): void {
	inFlight -= 1;
	const next = queue.shift();
	if (next) next();
}

export interface GeocodeResult {
	lat: number;
	lng: number;
}

/**
 * Extracts "State Zip" from a US-style full address (e.g. "123 Main St, Unit 4B, Los Angeles, CA 90028" → "CA 90028").
 * Used as a fallback when geocoding the full address fails.
 */
export function getStateZipFromAddress(address: string): string {
	const parts = address
		.split(",")
		.map((p) => p.trim())
		.filter(Boolean);
	if (parts.length >= 1) {
		return parts[parts.length - 1];
	}
	return address.trim();
}

export async function geocodeAddress(address: string): Promise<GeocodeResult | null> {
	const key = address.trim().replace(/\s+/g, " ").toLowerCase();
	if (!key) return null;
	const cached = CACHE.get(key);
	if (cached !== undefined) return cached === CACHED_EMPTY ? null : cached;

	await acquire();
	try {
		const url = new URL("https://nominatim.openstreetmap.org/search");
		url.searchParams.set("q", address.trim());
		url.searchParams.set("format", "json");
		url.searchParams.set("limit", "1");
		const res = await fetch(url.toString(), {
			headers: { "User-Agent": "PropertyListingApp/1.0 (contact@example.com)" },
		});
		if (!res.ok) return null;
		const data = (await res.json()) as Array<{ lat?: string; lon?: string }>;
		const first = data?.[0];
		if (!first?.lat || !first?.lon) {
			CACHE.set(key, CACHED_EMPTY);
			return null;
		}
		const lat = Number(first.lat);
		const lng = Number(first.lon);
		if (Number.isNaN(lat) || Number.isNaN(lng)) {
			CACHE.set(key, CACHED_EMPTY);
			return null;
		}
		const result = { lat, lng };
		CACHE.set(key, result);
		return result;
	} catch {
		return null;
	} finally {
		release();
	}
}
