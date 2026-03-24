import { useParams, Link } from "react-router";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import PropertyMap from "@/components/PropertyMap";
import { usePropertyDetail } from "@/hooks/usePropertyDetail";
import { useGeocode } from "@/hooks/useGeocode";

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
	const { listing, property, images, costs, features, loading, error } = usePropertyDetail(id);
	const addressForGeocode = property?.address?.replace(/\n/g, ", ") ?? null;
	const { coords: addressCoords } = useGeocode(addressForGeocode);

	if (loading) {
		return <PropertyDetailsSkeleton />;
	}

	if (error || (!listing && id)) {
		return (
			<div className="mx-auto max-w-[900px]">
				<div className="mb-4">
					<Link to="/properties" className="text-sm text-primary no-underline hover:underline">
						← Back to listings
					</Link>
				</div>
				<Card className="rounded-2xl border border-border shadow-sm">
					<CardContent className="pt-6">
						<p className="text-destructive">{error ?? "Listing not found."}</p>
					</CardContent>
				</Card>
			</div>
		);
	}

	const primaryImage = images.find((i) => i.imageType === "Primary") ?? images[0];
	const otherImages = images.filter((i) => i.id !== primaryImage?.id);

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
					{primaryImage?.imageUrl ? (
						<img
							src={primaryImage.imageUrl}
							alt={primaryImage.altText ?? primaryImage.name ?? "Property"}
							className="h-full w-full object-cover"
						/>
					) : (
						<Skeleton className="h-full w-full" />
					)}
				</div>
				<div className="flex flex-col gap-2">
					{otherImages.slice(0, 5).map((img) => (
						<div key={img.id} className="relative h-20 overflow-hidden rounded-lg bg-muted">
							{img.imageUrl ? (
								<img
									src={img.imageUrl}
									alt={img.altText ?? img.name ?? "Property"}
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
								label: listing?.name ?? property?.name ?? "Property",
							},
						]}
						className="h-[280px] w-full rounded-xl"
					/>
				</div>
			)}

			{/* Name, address, price (same order and price format as PropertyListingCard) */}
			<Card className="mb-4 rounded-2xl border border-border shadow-sm">
				<CardContent className="pt-3">
					<h1 className="mb-1.5 text-2xl font-semibold text-foreground">
						{listing?.name ?? property?.name ?? "Untitled"}
					</h1>
					{property?.address && (
						<p className="mb-1.5 text-sm text-muted-foreground">
							{property.address.replace(/\n/g, ", ")}
						</p>
					)}
					<p className="mb-4 text-2xl font-semibold text-primary">
						{listing?.listingPrice != null
							? formatListingPrice(listing.listingPrice)
							: property?.monthlyRent != null
								? formatListingPrice(property.monthlyRent) + " / Month"
								: "—"}
					</p>
					{/* Stat cards: value on top, label below, rounded panels (same order as reference) */}
					<div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{property?.bedrooms ?? "—"}
							</span>
							<span className="text-xs text-primary-foreground/90">Bedrooms</span>
						</div>
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{property?.bathrooms ?? "—"}
							</span>
							<span className="text-xs text-primary-foreground/90">Baths</span>
						</div>
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{property?.squareFootage ?? "—"}
							</span>
							<span className="text-xs text-primary-foreground/90">Square Feet</span>
						</div>
						<div className="flex flex-col items-center justify-center rounded-xl bg-primary px-4 py-3 text-center">
							<span className="text-xl font-semibold text-primary-foreground">
								{listing?.listingStatus ?? "Now"}
							</span>
							<span className="text-xs text-primary-foreground/90">Available</span>
						</div>
					</div>
					{property?.propertyType && (
						<p className="mt-3 text-sm text-muted-foreground">{property.propertyType}</p>
					)}
					{property?.description && (
						<p className="mt-4 text-sm text-foreground">{property.description}</p>
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
									key={c.id}
									className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border/50 pb-2 last:border-0"
								>
									<span className="text-sm font-medium">{c.category ?? "Cost"}</span>
									<span className="text-sm text-muted-foreground">{formatCurrency(c.amount)}</span>
									{c.date && (
										<span className="w-full text-xs text-muted-foreground">
											{formatDate(c.date)}
										</span>
									)}
									{c.description && <span className="w-full text-xs">{c.description}</span>}
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
									key={f.id}
									className="rounded-full border border-border bg-muted/60 px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
								>
									{f.category ? `${f.category}: ` : ""}
									{f.description ?? f.name ?? "—"}
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
					<Link to={`/application?listingId=${encodeURIComponent(id ?? "")}`}>
						Fill out an application
					</Link>
				</Button>
			</div>
		</div>
	);
}
