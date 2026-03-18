import { useSearchParams, Link } from "react-router";
import { useCallback, useEffect, useState, type ChangeEvent, type SubmitEvent } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent } from "../components/ui/card";
import {
	fetchListingById,
	fetchPropertyById,
	fetchPrimaryImagesByPropertyIds,
} from "@/api/propertyDetailGraphQL";
import { createApplicationRecord } from "@/api/applicationApi";
import { useAuth } from "../features/authentication/context/AuthContext";
import { fetchUserContact } from "../features/authentication/api/userProfileApi";

export default function Application() {
	const { user } = useAuth();
	const [searchParams] = useSearchParams();
	const listingId = searchParams.get("listingId") ?? "";

	const [listingName, setListingName] = useState<string | null>(null);
	const [propertyAddress, setPropertyAddress] = useState<string | null>(null);
	const [propertyId, setPropertyId] = useState<string | null>(null);
	const [propertyImageUrl, setPropertyImageUrl] = useState<string | null>(null);
	const [contactId, setContactId] = useState<string | null>(null);
	const [loading, setLoading] = useState(!!listingId);
	const [loadError, setLoadError] = useState<string | null>(null);

	const [moveInDate, setMoveInDate] = useState("");
	const [employment, setEmployment] = useState("");
	const [references, setReferences] = useState("");

	const [submitting, setSubmitting] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);
	const [submittedId, setSubmittedId] = useState<string | null>(null);

	useEffect(() => {
		if (!user?.id) return;
		let mounted = true;
		fetchUserContact<{ ContactId?: string }>(user.id)
			.then((contact) => {
				if (mounted) setContactId(contact.ContactId ?? null);
			})
			.catch((err) => {
				if (mounted) console.error("Failed to fetch contact ID", err);
			});
		return () => {
			mounted = false;
		};
	}, [user]);

	useEffect(() => {
		if (!listingId?.trim()) {
			setLoading(false);
			return;
		}
		let cancelled = false;
		setLoadError(null);
		(async () => {
			try {
				const listing = await fetchListingById(listingId);
				if (cancelled) return;
				if (!listing) {
					setLoadError("Listing not found.");
					setLoading(false);
					return;
				}
				setListingName(listing.name);
				if (listing.propertyId) {
					setPropertyId(listing.propertyId);
					const [property, primaryImages] = await Promise.all([
						fetchPropertyById(listing.propertyId),
						fetchPrimaryImagesByPropertyIds([listing.propertyId]),
					]);
					if (cancelled) return;
					setPropertyAddress(property?.address ?? null);
					setPropertyImageUrl(primaryImages[listing.propertyId] ?? null);
				}
			} catch (e) {
				if (!cancelled) {
					setLoadError(e instanceof Error ? e.message : "Failed to load listing.");
				}
			} finally {
				if (!cancelled) setLoading(false);
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [listingId]);

	const handleSubmit = useCallback(
		async (e: SubmitEvent<HTMLFormElement>) => {
			e.preventDefault();
			setSubmitError(null);
			setSubmitting(true);
			try {
				const id = await createApplicationRecord({
					Property__c: propertyId || null,
					Status__c: "Submitted",
					User__c: contactId || user?.id || "",
					Start_Date__c: moveInDate.trim() || null,
					Employment__c: employment.trim() || null,
					References__c: references.trim() || null,
				});
				setSubmittedId(id.id);
			} catch (err) {
				setSubmitError(err instanceof Error ? err.message : "Failed to submit application.");
			} finally {
				setSubmitting(false);
			}
		},
		[propertyId, contactId, moveInDate, employment, references],
	);

	if (loading) {
		return (
			<div className="mx-auto max-w-[900px]">
				<div className="mb-6 h-48 animate-pulse rounded-2xl bg-muted" />
				<div className="h-64 animate-pulse rounded-2xl bg-muted" />
			</div>
		);
	}

	if (submittedId) {
		return (
			<div className="mx-auto max-w-[900px]">
				<Card className="mb-6 rounded-2xl border border-border p-6 shadow-sm">
					<h2 className="mb-2 text-2xl font-semibold text-foreground">Application submitted</h2>
					<p className="text-sm text-muted-foreground">
						Your application has been saved. Reference: {submittedId}
					</p>
					<div className="mt-4 flex gap-2">
						<Link to="/properties" className="text-sm text-primary no-underline hover:underline">
							Back to search
						</Link>
						<Button
							asChild
							size="sm"
							className="rounded-xl bg-primary px-5 py-5 text-lg font-medium transition-colors duration-200 hover:bg-primary/90"
						>
							<Link to="/application">Submit another</Link>
						</Button>
					</div>
				</Card>
			</div>
		);
	}

	return (
		<div className="mx-auto max-w-[900px]">
			<div className="mb-4">
				<Link
					to={listingId ? `/property/${listingId}` : "/properties"}
					className="text-sm text-primary no-underline hover:underline"
				>
					{listingId ? "← Back to listing" : "← Back to search"}
				</Link>
			</div>
			<Card className="mb-6 flex gap-4 rounded-2xl border border-border p-6 shadow-sm">
				<div className="relative size-[200px] shrink-0 overflow-hidden rounded-xl bg-muted">
					{propertyImageUrl ? (
						<img src={propertyImageUrl} alt="" className="h-full w-full object-cover" />
					) : (
						<div className="h-full w-full bg-muted" aria-hidden />
					)}
				</div>
				<div className="min-w-0 flex-1">
					<h2 className="mb-1.5 text-2xl font-semibold text-foreground">
						{listingName ?? "Apply for a property"}
					</h2>
					<p className="text-sm text-muted-foreground">
						{propertyAddress ??
							(listingId
								? "Loading…"
								: "Select a property from search or listing detail to apply.")}
					</p>
					{loadError && <p className="mt-2 text-sm text-destructive">{loadError}</p>}
				</div>
			</Card>

			<Card className="mb-6 rounded-2xl border border-border shadow-sm">
				<CardContent className="pt-3">
					<form onSubmit={handleSubmit}>
						<div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
							<div className="space-y-2">
								<Label htmlFor="app-move-in">Move in date</Label>
								<Input
									id="app-move-in"
									type="date"
									value={moveInDate}
									onChange={(e: ChangeEvent<HTMLInputElement>) => setMoveInDate(e.target.value)}
								/>
							</div>
						</div>
						<div className="mb-4 space-y-2">
							<Label htmlFor="app-employment">Employment info</Label>
							<textarea
								id="app-employment"
								rows={3}
								className="min-h-[80px] w-full resize-y rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
								value={employment}
								onChange={(e) => setEmployment(e.target.value)}
							/>
						</div>
						<div className="mb-4 space-y-2">
							<Label htmlFor="app-references">References</Label>
							<textarea
								id="app-references"
								rows={3}
								className="min-h-[80px] w-full resize-y rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
								value={references}
								onChange={(e) => setReferences(e.target.value)}
							/>
						</div>
						{submitError && <p className="mb-4 text-sm text-destructive">{submitError}</p>}
						<div className="flex gap-2">
							<Button
								type="submit"
								size="sm"
								className="w-full cursor-pointer rounded-xl bg-primary px-5 py-5 text-lg font-medium transition-colors duration-200 hover:bg-primary/90 disabled:opacity-50"
								disabled={submitting}
							>
								{submitting ? "Submitting…" : "Submit application"}
							</Button>
						</div>
					</form>
				</CardContent>
			</Card>
		</div>
	);
}
