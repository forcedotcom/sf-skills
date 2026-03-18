/**
 * Fetches Maintenance_Request__c list and exposes refetch for after create.
 */
import { useState, useEffect, useCallback } from "react";
import {
	queryMaintenanceRequests,
	type MaintenanceRequestSummary,
} from "@/api/maintenanceRequestApi";

export function useMaintenanceRequests(): {
	requests: MaintenanceRequestSummary[];
	loading: boolean;
	error: string | null;
	refetch: () => Promise<void>;
} {
	const [requests, setRequests] = useState<MaintenanceRequestSummary[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchList = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const list = await queryMaintenanceRequests(50, null);
			setRequests(list);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Failed to load maintenance requests");
			setRequests([]);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchList();
	}, [fetchList]);

	return { requests, loading, error, refetch: fetchList };
}
