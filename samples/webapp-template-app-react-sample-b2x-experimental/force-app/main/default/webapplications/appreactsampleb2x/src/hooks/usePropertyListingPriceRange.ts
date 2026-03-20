/**
 * Fetches the available min/max listing price for the current search (no price/bedroom filters).
 * Use to render the filter bar only after knowing the available price range.
 */
import { useState, useEffect, useRef } from "react";
import { queryPropertyListingPriceRange } from "@/api/propertyListingGraphQL";

/** Cap for slider max when dataset has outliers; UI never sees a higher max. */
const SLIDER_PRICE_CAP = 50_000;

export interface PropertyListingPriceRange {
	priceMin: number;
	priceMax: number;
	/** True when raw max was > cap and we capped for the slider (show "50,000+"). */
	maxCapped?: boolean;
}

/** Fallback when the price-range API call fails. */
const DEFAULT_PRICE_RANGE: PropertyListingPriceRange = { priceMin: 0, priceMax: 100_000 };

function capPriceRange(range: { priceMin: number; priceMax: number }): PropertyListingPriceRange {
	if (range.priceMax <= SLIDER_PRICE_CAP)
		return { priceMin: range.priceMin, priceMax: range.priceMax };
	return {
		priceMin: range.priceMin,
		priceMax: SLIDER_PRICE_CAP,
		maxCapped: true,
	};
}

export function usePropertyListingPriceRange(searchQuery: string): {
	priceRange: PropertyListingPriceRange | null;
	loading: boolean;
	error: string | null;
} {
	const [priceRange, setPriceRange] = useState<PropertyListingPriceRange | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const cancelledRef = useRef(false);

	useEffect(() => {
		cancelledRef.current = false;
		setLoading(true);
		setError(null);
		queryPropertyListingPriceRange(searchQuery)
			.then((range) => {
				if (!cancelledRef.current) setPriceRange(range ? capPriceRange(range) : null);
			})
			.catch((err) => {
				if (!cancelledRef.current) {
					setError(err instanceof Error ? err.message : "Failed to load price range");
					setPriceRange(capPriceRange(DEFAULT_PRICE_RANGE));
				}
			})
			.finally(() => {
				if (!cancelledRef.current) setLoading(false);
			});
		return () => {
			cancelledRef.current = true;
		};
	}, [searchQuery]);

	return { priceRange, loading, error };
}
