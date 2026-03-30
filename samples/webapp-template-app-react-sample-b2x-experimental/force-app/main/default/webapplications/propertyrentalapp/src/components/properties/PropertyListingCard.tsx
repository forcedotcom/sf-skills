/**
 * Stacked property listing card: image on top, details below. Single price + bedrooms, amenity list, Apply button.
 * No phone or secondary price. Virtual Tours / Videos pills on image.
 */
import { useNavigate } from "react-router";
import { useCallback, type MouseEvent } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { PropertySearchNode } from "@/api/properties/propertySearchService";

function formatPrice(val: string | number | null | undefined): string {
	if (val == null) return "—";
	const n = typeof val === "number" ? val : Number(val);
	if (Number.isNaN(n)) return String(val);
	return (
		new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			maximumFractionDigits: 0,
		}).format(n) + "+"
	);
}

export interface PropertyListingCardProps {
	node: PropertySearchNode;
	imageUrl: string | null;
	address?: string | null;
	amenities?: string | null;
	/** Show skeleton while any supplementary data (image, address, amenities) is still loading. */
	loading?: boolean;
}

export function PropertyListingCardSkeleton() {
	return (
		<div
			className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm"
			role="status"
		>
			<Skeleton className="aspect-[16/10] w-full rounded-none" />
			<div className="space-y-3 p-3">
				<Skeleton className="h-6 w-3/4" />
				<Skeleton className="h-4 w-1/2" />
				<Skeleton className="h-6 w-1/3" />
				<div className="flex gap-1.5">
					<Skeleton className="h-5 w-16 rounded-full" />
					<Skeleton className="h-5 w-20 rounded-full" />
					<Skeleton className="h-5 w-14 rounded-full" />
				</div>
				<Skeleton className="h-11 w-full rounded-xl" />
			</div>
			<span className="sr-only">Loading property…</span>
		</div>
	);
}

export default function PropertyListingCard({
	node,
	imageUrl,
	address,
	amenities,
	loading = false,
}: PropertyListingCardProps) {
	const navigate = useNavigate();
	const name = node.Name?.displayValue ?? node.Name?.value ?? "Untitled";
	const price = node.Monthly_Rent__c?.value;
	const bedroomsNum = typeof node.Bedrooms__c?.value === "number" ? node.Bedrooms__c.value : NaN;
	const bedroomsLabel =
		!Number.isNaN(bedroomsNum) && bedroomsNum >= 0
			? `${bedroomsNum} Bedroom${bedroomsNum !== 1 ? "s" : ""}`
			: null;
	const detailPath = `/property/${node.Id}`;

	const handleClick = useCallback(() => {
		navigate(detailPath);
	}, [navigate, detailPath]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Enter" || e.key === " ") {
				e.preventDefault();
				handleClick();
			}
		},
		[handleClick],
	);

	if (loading) {
		return <PropertyListingCardSkeleton />;
	}

	const displayAddress = (address ?? "").trim().replace(/\n/g, ", ") || null;
	const amenityLabels = (amenities ?? "")
		.split(/\s*\|\s*/)
		.map((s) => s.trim())
		.filter(Boolean);

	return (
		<article
			className="flex h-full min-h-0 cursor-pointer flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-sm transition-all duration-200 hover:shadow-md focus-within:ring-2 focus-within:ring-primary focus-within:ring-offset-2"
			onClick={handleClick}
			onKeyDown={handleKeyDown}
			role="button"
			tabIndex={0}
			aria-label={`View details for ${name}`}
		>
			{/* Image on top, full width */}
			<div className="relative aspect-[16/10] w-full shrink-0 overflow-hidden rounded-t-2xl bg-muted">
				{imageUrl ? (
					<img src={imageUrl} alt="" className="h-full w-full object-cover" />
				) : (
					<div className="flex h-full items-center justify-center text-sm text-muted-foreground">
						No image
					</div>
				)}
				<div className="absolute left-1.5 top-1.5 flex flex-col gap-0.5">
					<span className="rounded-full bg-violet-600 px-2 py-0.5 text-xs font-medium text-white">
						Virtual Tours
					</span>
					<span className="rounded-full bg-violet-600/90 px-2 py-0.5 text-xs font-medium text-white">
						Videos
					</span>
				</div>
			</div>

			{/* Content below: name, address, price+beds, amenities, Apply */}
			<div className="flex min-h-0 flex-1 flex-col justify-between p-3">
				<div className="min-h-0">
					<div className="mb-1.5">
						<h3 className="text-2xl font-semibold text-foreground">{name}</h3>
						{displayAddress && (
							<p className="truncate text-sm text-muted-foreground">{displayAddress}</p>
						)}
					</div>

					{/* Single price + bedrooms – price bold, teal, 2x size */}
					<div className="mb-1.5 flex flex-wrap items-baseline gap-x-3 gap-y-0.5 text-base">
						{price != null && (
							<span className="text-2xl font-semibold text-primary">
								{formatPrice(price)}
								{bedroomsLabel != null ? (
									<span className="ml-1 text-base font-normal text-muted-foreground">
										{bedroomsLabel}
									</span>
								) : null}
							</span>
						)}
					</div>

					{/* Amenity pills */}
					{amenityLabels.length > 0 && (
						<div className="mb-2 flex flex-wrap gap-1.5">
							{amenityLabels.map((label) => (
								<span
									key={label}
									className="rounded-full border border-border bg-muted/60 px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
								>
									{label}
								</span>
							))}
						</div>
					)}
				</div>

				{/* Apply button */}
				<Button
					size="sm"
					className="mt-4 w-full cursor-pointer rounded-xl bg-primary px-5 py-5 text-lg font-medium transition-colors duration-200 hover:bg-primary/90"
					onClick={(e: MouseEvent<HTMLButtonElement>) => {
						e.stopPropagation();
						navigate(`/application?propertyId=${encodeURIComponent(node.Id)}`);
					}}
				>
					Apply
				</Button>
			</div>
		</article>
	);
}
