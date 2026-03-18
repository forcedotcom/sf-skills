import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Link } from "react-router";
import type { MaintenanceRequestSummary } from "@/api/maintenanceRequestApi";
import MaintenanceRequestListItem from "@/components/MaintenanceRequestListItem";
import MaintenanceDetailsModal from "@/components/MaintenanceDetailsModal";
import { WeatherWidget } from "@/components/WeatherWidget";
import { useMaintenanceRequests } from "@/hooks/useMaintenanceRequests";

export default function Dashboard() {
	const {
		requests: maintenanceRequests,
		loading: maintenanceLoading,
		error: maintenanceError,
	} = useMaintenanceRequests();
	const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequestSummary | null>(null);
	const recentMaintenance = maintenanceRequests.slice(0, 5);

	return (
		<div className="mx-auto flex max-w-[1100px] flex-col gap-6 lg:flex-row">
			{selectedRequest && (
				<MaintenanceDetailsModal
					request={selectedRequest}
					isOpen={!!selectedRequest}
					onClose={() => setSelectedRequest(null)}
				/>
			)}
			{/* Maintenance: full width on mobile, flexible on desktop so content is not clipped */}
			<div className="min-w-0 flex-1">
				<Card className="border-gray-200 p-6 shadow-sm">
					<div className="mb-6 flex items-center justify-between">
						<h2 className="text-lg font-semibold tracking-wide text-primary">
							Maintenance Requests
						</h2>
						<Link
							to="/maintenance/requests"
							className="cursor-pointer text-primary underline-offset-4 hover:underline"
						>
							See All
						</Link>
					</div>
					<CardContent className="space-y-4 p-0">
						{maintenanceLoading && (
							<p className="py-8 text-center text-sm text-muted-foreground">Loading…</p>
						)}
						{maintenanceError && (
							<p className="py-4 text-sm text-destructive" role="alert">
								{maintenanceError}
							</p>
						)}
						{!maintenanceLoading && !maintenanceError && recentMaintenance.length === 0 && (
							<div className="py-8 text-center text-gray-500">No maintenance requests</div>
						)}
						{!maintenanceLoading &&
							!maintenanceError &&
							recentMaintenance.map((request) => (
								<MaintenanceRequestListItem
									key={request.id}
									request={request}
									onClick={setSelectedRequest}
								/>
							))}
					</CardContent>
				</Card>
			</div>
			{/* Weather */}
			<div className="w-full shrink-0 lg:w-[320px]">
				<WeatherWidget />
			</div>
		</div>
	);
}
