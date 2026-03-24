import { useState } from "react";
import type { MaintenanceRequestSummary } from "@/api/maintenanceRequestApi";
import MaintenanceRequestListItem from "@/components/MaintenanceRequestListItem";
import MaintenanceDetailsModal from "@/components/MaintenanceDetailsModal";
import { SkeletonListRows } from "@/components/SkeletonPrimitives";

interface MaintenanceRequestListProps {
	requests: MaintenanceRequestSummary[];
	loading: boolean;
	error: string | null;
	emptyMessage?: string;
}

export default function MaintenanceRequestList({
	requests,
	loading,
	error,
	emptyMessage = "No maintenance requests",
}: MaintenanceRequestListProps) {
	const [selectedRequest, setSelectedRequest] = useState<MaintenanceRequestSummary | null>(null);

	return (
		<>
			{selectedRequest && (
				<MaintenanceDetailsModal
					request={selectedRequest}
					onClose={() => setSelectedRequest(null)}
				/>
			)}
			{loading && <SkeletonListRows count={3} />}
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
						key={request.id}
						request={request}
						onClick={setSelectedRequest}
					/>
				))}
		</>
	);
}
