import { useState, useEffect } from "react";
import { geocodeAddress, getStateZipFromAddress, type GeocodeResult } from "@/utils/geocode";

export function useGeocode(address: string | null | undefined): {
	coords: GeocodeResult | null;
	loading: boolean;
} {
	const [coords, setCoords] = useState<GeocodeResult | null>(null);
	const [loading, setLoading] = useState(false);

	useEffect(() => {
		if (!address?.trim()) {
			setCoords(null);
			setLoading(false);
			return;
		}
		let cancelled = false;
		setLoading(true);
		const normalized = address.replace(/\n/g, ", ").trim();

		(async () => {
			try {
				let result = await geocodeAddress(normalized);
				if (cancelled) return;
				if (result != null) {
					setCoords(result);
					return;
				}
				// Fallback: same as property search – try state + zip if full address failed
				const stateZip = getStateZipFromAddress(normalized);
				if (stateZip !== normalized) {
					result = await geocodeAddress(stateZip);
					if (!cancelled) setCoords(result);
				}
			} catch {
				if (!cancelled) setCoords(null);
			} finally {
				if (!cancelled) setLoading(false);
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [address?.trim() ?? ""]);

	return { coords, loading };
}
