import { useState, useCallback, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Calendar, ArrowRight } from "lucide-react";
import type { MaintenanceRequestSummary } from "@/api/maintenanceRequestApi";
import MaintenanceRequestListItem from "@/components/MaintenanceRequestListItem";
import MaintenanceDetailsModal from "@/components/MaintenanceDetailsModal";
import { useMaintenanceRequests } from "@/hooks/useMaintenanceRequests";
import { createMaintenanceRequest } from "@/api/maintenanceRequestApi";

const TYPE_OPTIONS = [
	"Plumbing",
	"Electrical",
	"HVAC",
	"Appliance",
	"Structural",
	"Cleaning",
	"Security",
	"Pest",
	"Other",
] as const;

const PRIORITY_OPTIONS = [
	{ value: "Standard", label: "Standard" },
	{ value: "High", label: "High (Same Day)" },
	{ value: "Emergency", label: "Emergency (2hr)" },
] as const;

export default function Maintenance() {
	const { requests, loading, error, refetch } = useMaintenanceRequests();
	const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequestSummary | null>(null);
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
				await refetch();
			} catch (err) {
				setSubmitError(err instanceof Error ? err.message : "Failed to submit request");
			} finally {
				setSubmitting(false);
			}
		},
		[title, description, type, priority, dateRequested, refetch],
	);

	return (
		<div className="mx-auto max-w-[900px]">
			{selectedRequest && (
				<MaintenanceDetailsModal
					request={selectedRequest}
					isOpen={!!selectedRequest}
					onClose={() => setSelectedRequest(null)}
				/>
			)}
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
										<option key={o} value={o}>
											{o}
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
								{submitError}
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
					<h2 className="text-lg font-semibold uppercase tracking-wide text-primary">
						Maintenance Requests
					</h2>
				</div>
				<CardContent className="space-y-4 p-0">
					{error && (
						<p className="py-4 text-sm text-destructive" role="alert">
							{error}
						</p>
					)}
					{loading && <p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>}
					{!loading && !error && requests.length === 0 && (
						<div className="py-8 text-center text-gray-500">
							No maintenance requests yet. Submit one above.
						</div>
					)}
					{!loading &&
						!error &&
						requests.map((request) => (
							<MaintenanceRequestListItem
								key={request.id}
								request={request}
								onClick={setSelectedRequest}
							/>
						))}
				</CardContent>
			</Card>
		</div>
	);
}
