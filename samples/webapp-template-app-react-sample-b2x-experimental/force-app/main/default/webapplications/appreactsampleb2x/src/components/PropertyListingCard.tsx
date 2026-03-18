/**
 * Stacked property listing card: image on top, details below. Single price + bedrooms, amenity list, Apply button.
 * No phone or secondary price. Virtual Tours / Videos pills on image.
 */
import { useNavigate } from "react-router";
import { useCallback, type MouseEvent } from "react";
import { Button } from "@/components/ui/button";
import type { SearchResultRecordData } from "@/features/global-search/types/search/searchResults.js";

function fieldDisplay(
	fields: Record<string, { value?: unknown; displayValue?: string | null }> | undefined,
	apiName: string,
): string | null {
	const f = fields?.[apiName];
	if (!f || typeof f !== "object") return null;
	if (f.displayValue != null && f.displayValue !== "") return String(f.displayValue);
	if (f.value != null) return typeof f.value === "object" ? null : String(f.value);
	return null;
}

function formatPrice(val: string | number | null): string {
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

interface PropertyListingCardProps {
	record: SearchResultRecordData;
	imageUrl: string | null;
	/** Property address (Address__c from Property__c) when available */
	address?: string | null;
	/** Amenities string (e.g. "In-unit washer | Pool | Gym"), separated by | */
	amenities?: string | null;
}

export default function PropertyListingCard({
	record,
	imageUrl,
	address,
	amenities,
}: PropertyListingCardProps) {
	const navigate = useNavigate();
	const name = fieldDisplay(record.fields, "Name") ?? "Untitled";
	const price = fieldDisplay(record.fields, "Listing_Price__c");
	const propertyRef = fieldDisplay(record.fields, "Property__c");
	const bedroomsRaw = fieldDisplay(record.fields, "Property__r.Bedrooms__c");
	const bedroomsNum = bedroomsRaw != null && bedroomsRaw !== "" ? Number(bedroomsRaw) : NaN;
	const bedroomsLabel =
		!Number.isNaN(bedroomsNum) && bedroomsNum >= 0
			? `${bedroomsNum} Bedroom${bedroomsNum !== 1 ? "s" : ""}`
			: null;
	const detailPath = `/property/${record.id}`;
	const displayAddress = (address ?? propertyRef ?? "").trim().replace(/\n/g, ", ") || null;

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

					{/* Amenity pills (fetched per property, string separated by |) */}
					{amenities != null && amenities.trim() !== "" && (
						<div className="mb-2 flex flex-wrap gap-1.5">
							{amenities
								.split(/\s*\|\s*/)
								.map((label) => label.trim())
								.filter(Boolean)
								.map((label) => (
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

				{/* Apply button – no phone, no email */}
				<Button
					size="sm"
					className="mt-4 w-full cursor-pointer rounded-xl bg-primary px-5 py-5 text-lg font-medium transition-colors duration-200 hover:bg-primary/90"
					onClick={(e: MouseEvent<HTMLButtonElement>) => {
						e.stopPropagation();
						navigate(`/application?listingId=${encodeURIComponent(record.id)}`);
					}}
				>
					Apply
				</Button>
			</div>
		</article>
	);
}
