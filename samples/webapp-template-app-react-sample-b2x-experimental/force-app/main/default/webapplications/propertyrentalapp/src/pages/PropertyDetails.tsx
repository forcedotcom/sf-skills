import { useParams, Link } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import PropertyMap from "@/components/properties/PropertyMap";
import { usePropertyDetail } from "@/hooks/usePropertyDetail";
import { useGeocode } from "@/hooks/useGeocode";
import type { GeocodeResult } from "@/utils/geocode";

function formatCurrency(val: number | string | null): string {
	if (val == null) return "—";
	const n = typeof val === "number" ? val : Number(val);
	return Number.isNaN(n)
		? String(val)
		: new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

/** Currency, no decimals. Used on detail page (no "+" suffix; card uses "+" for "and up"). */
function formatListingPrice(val: number | string | null): string {
	if (val == null) return "—";
	const n = typeof val === "number" ? val : Number(val);
	if (Number.isNaN(n)) return String(val);
	return new Intl.NumberFormat("en-US", {
		style: "currency",
		currency: "USD",
		maximumFractionDigits: 0,
	}).format(n);
}

function formatDate(val: string | null): string {
	if (!val) return "—";
	try {
		return new Date(val).toLocaleDateString();
	} catch {
		return val;
	}
}

function PropertyDetailsSkeleton() {
	return (
		<div className="mx-auto max-w-[900px]" role="status">
			<Skeleton className="mb-4 h-4 w-32" />

			<div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
				<Skeleton className="aspect-[4/3] rounded-xl" />
				<div className="flex flex-col gap-2">
					{Array.from({ length: 5 }, (_, i) => (
						<Skeleton key={i} className="h-20 rounded-lg" />
					))}
				</div>
			</div>

			<Skeleton className="mb-4 h-[280px] w-full rounded-xl" />

			<Card className="mb-4 rounded-2xl border border-border shadow-sm">
				<CardContent className="pt-3">
					<Skeleton className="mb-1.5 h-7 w-2/3" />
					<Skeleton className="mb-1.5 h-4 w-1/2" />
					<Skeleton className="mb-4 h-7 w-1/4" />
					<div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
						{Array.from({ length: 4 }, (_, i) => (
							<Skeleton key={i} className="h-[60px] rounded-xl" />
						))}
					</div>
					<Skeleton className="mt-3 h-3 w-24" />
					<Skeleton className="mt-4 h-4 w-full" />
					<Skeleton className="mt-1 h-4 w-3/4" />
				</CardContent>
			</Card>

			<Card className="mb-4 rounded-2xl border border-border shadow-sm">
				<CardHeader>
					<Skeleton className="h-5 w-28" />
				</CardHeader>
				<CardContent className="space-y-2">
					{Array.from({ length: 3 }, (_, i) => (
						<div
							key={i}
							className="flex items-baseline justify-between border-b border-border/50 pb-2 last:border-0"
						>
							<Skeleton className="h-4 w-24" />
							<Skeleton className="h-4 w-16" />
						</div>
					))}
				</CardContent>
			</Card>

			<Card className="mb-4 rounded-2xl border border-border shadow-sm">
				<CardHeader>
					<Skeleton className="h-5 w-40" />
				</CardHeader>
				<CardContent>
					<div className="flex flex-wrap gap-1.5">
						{Array.from({ length: 6 }, (_, i) => (
							<Skeleton key={i} className="h-6 w-20 rounded-full" />
						))}
					</div>
				</CardContent>
			</Card>

			<Skeleton className="mb-4 h-[52px] w-full rounded-xl" />

			<span className="sr-only">Loading property details…</span>
		</div>
	);
}

export default function PropertyDetails() {
	const { id } = useParams<{ id: string }>();
	const { property, loading, error } = usePropertyDetail(id);

	// Extract nested relationships from the single property node.
	const images = (property?.Property_Images__r?.edges ?? []).flatMap((e) =>
		e?.node ? [e.node] : [],
	);
	const features = (property?.Property_Features__r?.edges ?? []).flatMap((e) =>
		e?.node ? [e.node] : [],
	);
	const costs = (property?.Property_Costs__r?.edges ?? []).flatMap((e) =>
		e?.node ? [e.node] : [],
	);
	const listing = property?.Property_Listings__r?.edges?.[0]?.node ?? null;

	const addressForGeocode = property?.Address__c?.value?.replace(/\n/g, ", ") ?? null;
	const hasCoordinates =
		property?.Coordinates__Latitude__s?.value != null &&
		property?.Coordinates__Longitude__s?.value != null;
	// Always call hook in the same order; disable geocoding when coordinates already exist.
	const { coords: geocodedCoords } = useGeocode(hasCoordinates ? null : addressForGeocode);
	const addressCoords: GeocodeResult | null = hasCoordinates
		? {
				lat: Number(property!.Coordinates__Latitude__s!.value),
				lng: Number(property!.Coordinates__Longitude__s!.value),
			}
		: geocodedCoords;

	if (loading) {
		return <PropertyDetailsSkeleton />;
	}

	if (error) {
		return (
			<div className="mx-auto max-w-[900px]">
				<div className="mb-4">
					<Link to="/properties" className="text-sm text-primary no-underline hover:underline">
						← Back to listings
					</Link>
				</div>
				<Card className="rounded-2xl border border-border shadow-sm">
					<CardContent className="pt-6">
						<p className="text-destructive">Something went wrong. Please try again later.</p>
					</CardContent>
				</Card>
			</div>
		);
	}

	if (!property && id) {
		return (
			<div className="mx-auto max-w-[900px]">
				<div className="mb-4">
					<Link to="/properties" className="text-sm text-primary no-underline hover:underline">
						← Back to listings
					</Link>
				</div>
				<Card className="rounded-2xl border border-border shadow-sm">
					<CardContent className="pt-6">
						<p className="text-destructive">Listing not found.</p>
					</CardContent>
				</Card>
			</div>
		);
	}

	const primaryImage = images.find((i) => i.Image_Type__c?.value === "Primary") ?? images[0];
	const otherImages = images.filter((i) => i.Id !== primaryImage?.Id);

	return (
		<div className="mx-auto max-w-[900px]">
			<div className="mb-4">
				<Link to="/properties" className="text-sm text-primary no-underline hover:underline">
					← Back to listings
				</Link>
			</div>

			{/* Hero image + thumbnails */}
			<div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
				<div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-muted">
					{primaryImage?.Image_URL__c?.value ? (
						<img
							src={primaryImage.Image_URL__c.value}
							alt={primaryImage.Alt_Text__c?.value ?? primaryImage.Name?.value ?? "Property"}
							className="h-full w-full object-cover"
						/>
					) : (
						<Skeleton className="h-full w-full" />
					)}
				</div>
				<div className="flex flex-col gap-2">
					{otherImages.slice(0, 5).map((img) => (
						<div key={img.Id} className="relative h-20 overflow-hidden rounded-lg bg-muted">
							{img.Image_URL__c?.value ? (
								<img
									src={img.Image_URL__c.value}
									alt={img.Alt_Text__c?.value ?? img.Name?.value ?? "Property"}
									className="h-full w-full object-cover"
								/>
							) : null}
						</div>
					))}
				</div>
			</div>

			{/* Map - geocoded from property address */}
			{addressCoords && (
				<div className="mb-4">
					<PropertyMap
						center={[addressCoords.lat, addressCoords.lng]}
						zoom={15}
						markers={[
							{
								lat: addressCoords.lat,
								lng: addressCoords.lng,
								label: listing?.Name?.value ?? property?.Name?.value ?? "Property",
							},
						]}
						className="h-[280px] w-full rounded-xl"
					/>
				</div>
			)}

			{/* Name, address, price */}
			<Card className="mb-4 rounded-2xl border border-border shadow-sm">
				<CardContent className="pt-3">
					<h1 className="mb-1.5 text-2xl font-semibold text-foreground">
						{listing?.Name?.value ?? property?.Name?.value ?? "Untitled"}
					</h1>
					{property?.Address__c?.value && (
						<p className="mb-1.5 text-sm text-muted-foreground">
							{property.Address__c.value.replace(/\n/g, ", ")}
						</p>
					)}
					<p className="mb-4 text-2xl font-semibold text-primary">
						{listing?.Listing_Price__c?.value != null
							? formatListingPrice(listing.Listing_Price__c.value)
							: property?.Monthly_Rent__c?.value != null
								? formatListingPrice(property.Monthly_Rent__c.value) + " / Month"
								: "—"}
					</p>
					{/* Stat cards */}
					<div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{property?.Bedrooms__c?.value ?? "—"}
							</span>
							<span className="text-xs text-primary-foreground/90">Bedrooms</span>
						</div>
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{property?.Bathrooms__c?.value ?? "—"}
							</span>
							<span className="text-xs text-primary-foreground/90">Baths</span>
						</div>
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{property?.Sq_Ft__c?.value ?? "—"}
							</span>
							<span className="text-xs text-primary-foreground/90">Square Feet</span>
						</div>
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{listing?.Listing_Status__c?.value ?? "Now"}
							</span>
							<span className="text-xs text-primary-foreground/90">Available</span>
						</div>
					</div>
					{property?.Type__c?.value && (
						<p className="mt-3 text-sm text-muted-foreground">{property.Type__c.value}</p>
					)}
					{property?.Description__c?.value && (
						<p className="mt-4 text-sm text-foreground">{property.Description__c.value}</p>
					)}
				</CardContent>
			</Card>

			{/* Related: Costs */}
			{costs.length > 0 && (
				<Card className="mb-4 rounded-2xl border border-border shadow-sm">
					<CardHeader>
						<CardTitle className="text-base font-semibold">Related costs</CardTitle>
					</CardHeader>
					<CardContent>
						<ul className="space-y-2">
							{costs.slice(0, 10).map((c) => (
								<li
									key={c.Id}
									className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border/50 pb-2 last:border-0"
								>
									<span className="text-sm font-medium">{c.Cost_Category__c?.value ?? "Cost"}</span>
									<span className="text-sm text-muted-foreground">
										{formatCurrency(c.Cost_Amount__c?.value ?? null)}
									</span>
									{c.Cost_Date__c?.value && (
										<span className="w-full text-xs text-muted-foreground">
											{formatDate(c.Cost_Date__c.value)}
										</span>
									)}
									{c.Description__c?.value && (
										<span className="w-full text-xs">{c.Description__c.value}</span>
									)}
								</li>
							))}
						</ul>
						{costs.length > 10 && (
							<p className="mt-2 text-xs text-muted-foreground">+ {costs.length - 10} more</p>
						)}
					</CardContent>
				</Card>
			)}

			{/* Related: Features */}
			{features.length > 0 && (
				<Card className="mb-4 rounded-2xl border border-border shadow-sm">
					<CardHeader>
						<CardTitle className="text-base font-semibold">Features & amenities</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="flex flex-wrap gap-1.5">
							{features.map((f) => (
								<span
									key={f.Id}
									className="rounded-full border border-border bg-muted/60 px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
								>
									{f.Feature_Category__c?.value ? `${f.Feature_Category__c.value}: ` : ""}
									{f.Description__c?.value ?? f.Name?.value ?? "—"}
								</span>
							))}
						</div>
					</CardContent>
				</Card>
			)}

			<div className="mb-4">
				<Button
					asChild
					size="sm"
					className="w-full cursor-pointer rounded-xl bg-primary px-5 py-5 text-lg font-medium transition-colors duration-200 hover:bg-primary/90"
				>
					<Link to={`/application?propertyId=${encodeURIComponent(id ?? "")}`}>
						Fill out an application
					</Link>
				</Button>
			</div>
		</div>
	);
}
