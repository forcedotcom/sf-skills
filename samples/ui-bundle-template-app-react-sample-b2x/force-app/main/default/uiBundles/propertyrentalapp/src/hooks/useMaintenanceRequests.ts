/**
 * Fetches Maintenance_Request__c list and exposes refetch for after create.
 */
import { useState, useCallback } from "react";
import {
	searchMaintenanceRequests,
	type MaintenanceRequestNode,
} from "@/api/maintenanceRequests/maintenanceRequestApi";
import { ResultOrder } from "@/api/graphql-operations-types";
import { useAsyncData } from "@/hooks/useAsyncData";

async function fetchMaintenanceNodes(): Promise<MaintenanceRequestNode[]> {
	const result = await searchMaintenanceRequests({
		first: 50,
		orderBy: { Scheduled__c: { order: ResultOrder.Desc } },
	});
	return (result.edges ?? []).flatMap((e) => (e?.node ? [e.node] : []));
}

export function useMaintenanceRequests(): {
	requests: MaintenanceRequestNode[];
	loading: boolean;
	error: string | null;
	refetch: () => void;
} {
	const [generation, setGeneration] = useState(0);

	const { data, loading, error } = useAsyncData(fetchMaintenanceNodes, [generation]);

	const refetch = useCallback(() => {
		setGeneration((g) => g + 1);
	}, []);

	return { requests: data ?? [], loading, error, refetch };
}
