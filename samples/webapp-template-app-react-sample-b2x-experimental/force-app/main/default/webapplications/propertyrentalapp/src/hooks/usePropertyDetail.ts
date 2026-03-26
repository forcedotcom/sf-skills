/**
 * Fetches Property_Listing__c by id, then related Property__c, images, costs, and features.
 */
import { useState, useEffect, useCallback } from "react";
import {
	fetchListingById,
	fetchPropertyById,
	fetchImagesByPropertyId,
	fetchCostsByPropertyId,
	fetchFeaturesByPropertyId,
	type ListingDetail,
	type PropertyDetail,
	type PropertyImageRecord,
	type PropertyCostRecord,
	type PropertyFeatureRecord,
} from "@/api/properties/propertyDetailGraphQL";

export interface PropertyDetailState {
	listing: ListingDetail | null;
	property: PropertyDetail | null;
	images: PropertyImageRecord[];
	costs: PropertyCostRecord[];
	features: PropertyFeatureRecord[];
	loading: boolean;
	error: string | null;
}

export function usePropertyDetail(
	listingId: string | undefined,
): PropertyDetailState & { refetch: () => void } {
	const [listing, setListing] = useState<ListingDetail | null>(null);
	const [property, setProperty] = useState<PropertyDetail | null>(null);
	const [images, setImages] = useState<PropertyImageRecord[]>([]);
	const [costs, setCosts] = useState<PropertyCostRecord[]>([]);
	const [features, setFeatures] = useState<PropertyFeatureRecord[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const load = useCallback(async () => {
		if (!listingId?.trim()) {
			setListing(null);
			setProperty(null);
			setImages([]);
			setCosts([]);
			setFeatures([]);
			setLoading(false);
			setError(null);
			return;
		}
		setLoading(true);
		setError(null);
		try {
			const listingData = await fetchListingById(listingId);
			setListing(listingData ?? null);
			if (!listingData?.propertyId) {
				setProperty(null);
				setImages([]);
				setCosts([]);
				setFeatures([]);
				setLoading(false);
				return;
			}
			const [propertyData, imagesData, costsData, featuresData] = await Promise.all([
				fetchPropertyById(listingData.propertyId),
				fetchImagesByPropertyId(listingData.propertyId),
				fetchCostsByPropertyId(listingData.propertyId),
				fetchFeaturesByPropertyId(listingData.propertyId),
			]);
			setProperty(propertyData ?? null);
			setImages(imagesData ?? []);
			setCosts(costsData ?? []);
			setFeatures(featuresData ?? []);
		} catch (e) {
			setError(e instanceof Error ? e.message : String(e));
			setListing(null);
			setProperty(null);
			setImages([]);
			setCosts([]);
			setFeatures([]);
		} finally {
			setLoading(false);
		}
	}, [listingId]);

	useEffect(() => {
		load();
	}, [load]);

	return {
		listing,
		property,
		images,
		costs,
		features,
		loading,
		error,
		refetch: load,
	};
}
