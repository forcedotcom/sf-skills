import { useSearchParams, Link } from "react-router";
import { useCallback, useState, type ChangeEvent, type SubmitEvent } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent } from "../components/ui/card";
import { Skeleton } from "../components/ui/skeleton";
import { SkeletonField } from "@/components/SkeletonPrimitives";
import { fetchPropertyDetailById } from "@/api/properties/propertyDetailGraphQL";
import { createApplicationRecord } from "@/api/applications/applicationApi";
import { useAuth } from "@/features/authentication/context/AuthContext";
import { fetchUserContact } from "../features/authentication/api/userProfileApi";
import { useCachedAsyncData } from "@/features/object-search/hooks/useCachedAsyncData";

function ApplicationSkeleton() {
	return (
		<div className="mx-auto max-w-[900px]" role="status">
			<Skeleton className="mb-4 h-4 w-28" />

			<Card className="mb-6 flex gap-4 rounded-2xl border border-border p-6 shadow-sm">
				<Skeleton className="size-[200px] shrink-0 rounded-xl" />
				<div className="min-w-0 flex-1 space-y-2">
					<Skeleton className="h-7 w-2/3" />
					<Skeleton className="h-4 w-1/2" />
				</div>
			</Card>

			<Card className="mb-6 rounded-2xl border border-border shadow-sm">
				<CardContent className="space-y-4 pt-3">
					<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
						<SkeletonField labelWidth="w-20" />
					</div>
					<SkeletonField labelWidth="w-24" height="h-[80px]" />
					<SkeletonField labelWidth="w-20" height="h-[80px]" />
					<Skeleton className="h-12 w-full rounded-xl" />
				</CardContent>
			</Card>

			<span className="sr-only">Loading…</span>
		</div>
	);
}

export default function Application() {
	const { user } = useAuth();
	const [searchParams] = useSearchParams();
	const propertyId = searchParams.get("propertyId") ?? "";

	const { data: contactData } = useCachedAsyncData(
		() => {
			if (!user?.id) return Promise.resolve(null);
			return fetchUserContact<{ ContactId?: string }>(user.id);
		},
		[user?.id],
		{ key: `contact:${user?.id ?? ""}`, ttl: 300_000 },
	);
	const contactId = contactData?.ContactId ?? null;

	const {
		data: property,
		loading,
		error: loadError,
	} = useCachedAsyncData(
		() => {
			if (!propertyId?.trim()) return Promise.resolve(null);
			return fetchPropertyDetailById(propertyId);
		},
		[propertyId],
		{ key: `app-property:${propertyId}` },
	);

	const listing = property?.Property_Listings__r?.edges?.[0]?.node ?? null;
	const images = (property?.Property_Images__r?.edges ?? []).flatMap((e) =>
		e?.node ? [e.node] : [],
	);
	const primaryImage =
		images.find((i) => i.Image_Type__c?.value === "Primary") ?? images[0] ?? null;
	const propertyImageUrl = primaryImage?.Image_URL__c?.value ?? null;
	const propertyName = listing?.Name?.value ?? property?.Name?.value ?? null;
	const propertyAddress = property?.Address__c?.value ?? null;

	const [moveInDate, setMoveInDate] = useState("");
	const [employment, setEmployment] = useState("");
	const [references, setReferences] = useState("");

	const [submitting, setSubmitting] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);
	const [submittedId, setSubmittedId] = useState<string | null>(null);

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
		[propertyId, contactId, moveInDate, employment, references, user?.id],
	);

	if (loading) {
		return <ApplicationSkeleton />;
	}

	if (submittedId) {
		return (
			<div className="mx-auto max-w-[900px]">
				<Card className="mb-6 rounded-2xl border border-border p-6 shadow-sm">
					<h2 className="mb-2 text-2xl font-semibold text-foreground">Application submitted</h2>
					<p className="text-sm text-muted-foreground">
						Your application has been saved. Reference: {submittedId}
					</p>
					<div className="mt-4 flex gap-2 items-center">
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
					to={propertyId ? `/property/${propertyId}` : "/properties"}
					className="text-sm text-primary no-underline hover:underline"
				>
					{propertyId ? "← Back to listing" : "← Back to search"}
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
						{propertyName ?? "Apply for a property"}
					</h2>
					<p className="text-sm text-muted-foreground">
						{propertyAddress ??
							(propertyId ? (
								<Skeleton className="mt-1 h-4 w-48" />
							) : (
								"Select a property from search or listing detail to apply."
							))}
					</p>
					{loadError && (
						<p className="mt-2 text-sm text-destructive">
							Something went wrong. Please try again later.
						</p>
					)}
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
						{submitError && (
							<p className="mb-4 text-sm text-destructive">
								Something went wrong. Please try again later.
							</p>
						)}
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
