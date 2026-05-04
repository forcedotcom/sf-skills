import { useState, useCallback, useMemo, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Calendar, ArrowRight } from "lucide-react";
import MaintenanceRequestList from "@/components/maintenanceRequests/MaintenanceRequestList";
import { SkeletonListRows, SkeletonField } from "@/components/SkeletonPrimitives";
import {
	searchMaintenanceRequests,
	createMaintenanceRequest,
	type MaintenanceRequestNode,
} from "@/api/maintenanceRequests/maintenanceRequestApi";
import { useAuth } from "@/features/authentication/context/AuthContext";
import {
	useObjectSearchParams,
	type PaginationConfig,
} from "@/features/object-search/hooks/useObjectSearchParams";
import {
	useCachedAsyncData,
	clearCacheEntry,
} from "@/features/object-search/hooks/useCachedAsyncData";
import PaginationControls from "@/features/object-search/components/PaginationControls";
import type {
	Maintenance_Request__C_Filter,
	Maintenance_Request__C_OrderBy,
} from "@/api/graphql-operations-types";
import { ResultOrder } from "@/api/graphql-operations-types";
import type { FilterFieldConfig } from "@/features/object-search/utils/filterUtils";
import type { SortFieldConfig } from "@/features/object-search/utils/sortUtils";

const TYPE_OPTIONS = [
	{ value: "Plumbing", label: "Plumbing" },
	{ value: "Electrical", label: "Electrical" },
	{ value: "HVAC", label: "HVAC" },
	{ value: "Appliance", label: "Appliance" },
	{ value: "Carpentry", label: "Carpentry" },
	{ value: "Landscaping", label: "Landscaping" },
	{ value: "Cleaning", label: "Cleaning" },
	{ value: "Pest", label: "Pest Control" },
	{ value: "Other", label: "Other" },
] as const;

const PRIORITY_OPTIONS = [
	{ value: "Standard", label: "Standard" },
	{ value: "High", label: "High (Same Day)" },
	{ value: "Emergency", label: "Emergency (2hr)" },
] as const;

const FILTER_CONFIGS: FilterFieldConfig[] = [];

const SORT_CONFIGS: SortFieldConfig[] = [{ field: "Scheduled__c", label: "Scheduled" }];

const PAGINATION_CONFIG: PaginationConfig = {
	defaultPageSize: 10,
	validPageSizes: [10, 20, 50],
};

function MaintenanceSkeleton() {
	return (
		<div className="mx-auto max-w-[900px]" role="status">
			<Card className="mb-6 rounded-2xl shadow-md">
				<CardHeader>
					<Skeleton className="h-6 w-1/3" />
				</CardHeader>
				<CardContent className="space-y-4">
					{Array.from({ length: 2 }, (_, i) => (
						<div key={i} className="grid grid-cols-1 gap-4 md:grid-cols-2">
							<SkeletonField labelWidth="w-1/4" />
							<SkeletonField labelWidth="w-1/4" />
						</div>
					))}
					<SkeletonField labelWidth="w-1/6" height="h-[100px]" />
					<div className="flex justify-end">
						<Skeleton className="h-9 w-36" />
					</div>
				</CardContent>
			</Card>
			<Card className="border-gray-200 p-6 shadow-sm">
				<Skeleton className="mb-6 h-5 w-1/4" />
				<CardContent className="space-y-3 p-0">
					<SkeletonListRows />
				</CardContent>
			</Card>
			<span className="sr-only">Loading maintenance…</span>
		</div>
	);
}

export default function Maintenance() {
	const { loading: authLoading } = useAuth();

	const { query, pagination } = useObjectSearchParams<
		Maintenance_Request__C_Filter,
		Maintenance_Request__C_OrderBy
	>(FILTER_CONFIGS, SORT_CONFIGS, PAGINATION_CONFIG);

	const [refreshCounter, setRefreshCounter] = useState(0);

	const searchKey = `maintenance-requests:${JSON.stringify({
		orderBy: query.orderBy,
		first: pagination.pageSize,
		after: pagination.afterCursor,
		refresh: refreshCounter,
	})}`;

	const {
		data: searchResult,
		loading,
		error,
	} = useCachedAsyncData(
		() =>
			searchMaintenanceRequests({
				where: query.where,
				orderBy: { Scheduled__c: { order: ResultOrder.Desc } },
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, query.orderBy, pagination.pageSize, pagination.afterCursor, refreshCounter],
		{ key: searchKey },
	);

	const requests = useMemo(
		() =>
			(searchResult?.edges ?? []).reduce<MaintenanceRequestNode[]>((acc, edge) => {
				if (edge?.node) acc.push(edge.node);
				return acc;
			}, []),
		[searchResult?.edges],
	);

	const pageInfo = searchResult?.pageInfo;
	const hasNextPage = pageInfo?.hasNextPage ?? false;
	const hasPreviousPage = pagination.pageIndex > 0;

	const [title, setTitle] = useState("");
	const [description, setDescription] = useState("");
	const [type, setType] = useState<string>("");
	const [priority, setPriority] = useState<string>("Standard");
	const [dateRequested, setDateRequested] = useState(() => {
		const d = new Date();
		return d.toISOString().slice(0, 10);
	});
	const [submitting, setSubmitting] = useState(false);
	const [submitError, setSubmitError] = useState<string | null>(null);
	const [submitSuccess, setSubmitSuccess] = useState(false);

	const handleSubmit = useCallback(
		async (e: React.FormEvent) => {
			e.preventDefault();
			const t = title.trim();
			const desc = description.trim();
			if (!t && !desc) {
				setSubmitError("Title or description is required");
				return;
			}
			setSubmitting(true);
			setSubmitError(null);
			setSubmitSuccess(false);
			try {
				await createMaintenanceRequest({
					Description__c: desc || t,
					Type__c: type.trim() || undefined,
					Priority__c: priority,
					Status__c: "New",
					Scheduled__c: dateRequested ? new Date(dateRequested).toISOString() : undefined,
				});
				setSubmitSuccess(true);
				setTitle("");
				setDescription("");
				setType("");
				setPriority("Standard");
				setDateRequested(new Date().toISOString().slice(0, 10));
				clearCacheEntry(searchKey);
				setRefreshCounter((c) => c + 1);
			} catch (err) {
				setSubmitError(err instanceof Error ? err.message : "Failed to submit request");
			} finally {
				setSubmitting(false);
			}
		},
		[title, description, type, priority, dateRequested, searchKey],
	);

	if (authLoading) return <MaintenanceSkeleton />;

	return (
		<div className="mx-auto max-w-[900px]">
			<Card className="mb-6 rounded-2xl shadow-md">
				<CardHeader>
					<CardTitle className="text-2xl text-primary">New maintenance request</CardTitle>
				</CardHeader>
				<CardContent className="space-y-4">
					<form onSubmit={handleSubmit} className="space-y-4">
						<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
							<div className="space-y-2">
								<Label htmlFor="maintenance-title">Title *</Label>
								<Input
									id="maintenance-title"
									type="text"
									value={title}
									onChange={(e: ChangeEvent<HTMLInputElement>) => setTitle(e.target.value)}
									placeholder="e.g. Kitchen faucet leak"
									aria-label="Title"
									required
								/>
							</div>
							<div className="space-y-2">
								<Label htmlFor="maintenance-priority">Priority</Label>
								<select
									id="maintenance-priority"
									className="flex h-9 w-full rounded-xl border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-[color,box-shadow] duration-200 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary"
									aria-label="Priority"
									value={priority}
									onChange={(e: ChangeEvent<HTMLSelectElement>) => setPriority(e.target.value)}
								>
									{PRIORITY_OPTIONS.map((o) => (
										<option key={o.value} value={o.value}>
											{o.label}
										</option>
									))}
								</select>
							</div>
						</div>
						<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
							<div className="space-y-2">
								<Label htmlFor="maintenance-date">Date reported</Label>
								<div className="relative">
									<Input
										id="maintenance-date"
										type="date"
										value={dateRequested}
										onChange={(e: ChangeEvent<HTMLInputElement>) =>
											setDateRequested(e.target.value)
										}
										className="pr-10"
										aria-label="Date reported"
									/>
									<span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
										<Calendar className="size-[18px] text-muted-foreground" aria-hidden />
									</span>
								</div>
							</div>
							<div className="space-y-2">
								<Label htmlFor="maintenance-type">Type</Label>
								<select
									id="maintenance-type"
									className="flex h-9 w-full rounded-xl border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-[color,box-shadow] duration-200 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary"
									aria-label="Type"
									value={type}
									onChange={(e: ChangeEvent<HTMLSelectElement>) => setType(e.target.value)}
								>
									<option value="">—</option>
									{TYPE_OPTIONS.map((o) => (
										<option key={o.value} value={o.value}>
											{o.label}
										</option>
									))}
								</select>
							</div>
						</div>
						<div className="space-y-2">
							<Label htmlFor="maintenance-description">Description</Label>
							<textarea
								id="maintenance-description"
								rows={4}
								placeholder="Describe the issue"
								className="min-h-[100px] w-full resize-y rounded-xl border border-input bg-transparent px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary transition-colors duration-200"
								aria-label="Description"
								value={description}
								onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)}
							/>
						</div>
						{submitError && (
							<p className="text-sm text-destructive" role="alert">
								Something went wrong. Please try again later.
							</p>
						)}
						{submitSuccess && (
							<p className="text-sm text-green-600" role="status">
								Request submitted. It will appear in the list below.
							</p>
						)}
						<div className="flex justify-end">
							<Button
								type="submit"
								className="cursor-pointer gap-2 rounded-xl transition-colors duration-200"
								disabled={submitting}
							>
								{submitting ? "Submitting…" : "Submit Request"}
								<ArrowRight className="size-[18px]" aria-hidden />
							</Button>
						</div>
					</form>
				</CardContent>
			</Card>
			<Card className="border-gray-200 p-6 shadow-sm">
				<div className="mb-6">
					<h2 className="text-lg font-semibold tracking-wide text-primary">Maintenance Requests</h2>
				</div>
				<CardContent className="space-y-4 p-0">
					<MaintenanceRequestList
						requests={requests}
						loading={loading}
						error={error}
						emptyMessage="No maintenance requests yet. Submit one above."
					/>
				</CardContent>
				{!loading && !error && requests.length > 0 && (
					<div className="px-6 pb-6">
						<PaginationControls
							pageIndex={pagination.pageIndex}
							hasNextPage={hasNextPage}
							hasPreviousPage={hasPreviousPage}
							pageSize={pagination.pageSize}
							pageSizeOptions={PAGINATION_CONFIG.validPageSizes}
							onNextPage={() => {
								if (pageInfo?.endCursor) pagination.goToNextPage(pageInfo.endCursor);
							}}
							onPreviousPage={pagination.goToPreviousPage}
							onPageSizeChange={pagination.setPageSize}
							disabled={loading || !!error}
						/>
					</div>
				)}
			</Card>
		</div>
	);
}
