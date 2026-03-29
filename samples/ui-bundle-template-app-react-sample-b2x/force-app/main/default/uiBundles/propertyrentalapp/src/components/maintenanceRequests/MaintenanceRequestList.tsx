import { useState } from "react";
import type { MaintenanceRequestNode } from "@/api/maintenanceRequests/maintenanceRequestApi";
import MaintenanceRequestListItem from "@/components/maintenanceRequests/MaintenanceRequestListItem";
import MaintenanceSummaryDetailsModal from "@/components/maintenanceRequests/MaintenanceSummaryDetailsModal";
import { SkeletonListRows } from "@/components/SkeletonPrimitives";

interface MaintenanceRequestListProps {
	requests: MaintenanceRequestNode[];
	loading: boolean;
	error: string | null;
	emptyMessage?: string;
	skeletonCount?: number;
}

export default function MaintenanceRequestList({
	requests,
	loading,
	error,
	emptyMessage = "No maintenance requests",
	skeletonCount = 3,
}: MaintenanceRequestListProps) {
	const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequestNode | null>(null);

	return (
		<>
			{selectedRequest && (
				<MaintenanceSummaryDetailsModal
					request={selectedRequest}
					onClose={() => setSelectedRequest(null)}
				/>
			)}
			{loading && <SkeletonListRows count={skeletonCount} />}
			{error && (
				<p className="py-4 text-sm text-destructive" role="alert">
					{error}
				</p>
			)}
			{!loading && !error && requests.length === 0 && (
				<div className="py-8 text-center text-gray-500">{emptyMessage}</div>
			)}
			{!loading &&
				!error &&
				requests.map((request) => (
					<MaintenanceRequestListItem
						key={request.Id}
						request={request}
						onClick={setSelectedRequest}
					/>
				))}
		</>
	);
}
