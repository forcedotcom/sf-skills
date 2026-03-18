import type { MaintenanceWorker } from "../lib/types";
import { getAllMaintenanceRequests } from "./maintenance";

/**
 * Fetches maintenance workers. Derives unique workers from maintenance requests
 * (assigned workers) and adds fallback placeholder entries so the list is never empty.
 */
export async function getMaintenanceWorkers(): Promise<MaintenanceWorker[]> {
	try {
		const requests = await getAllMaintenanceRequests(200);
		const byName = new Map<string, MaintenanceWorker>();
		let idCounter = 1;
		for (const req of requests) {
			const name = req.assignedWorkerName || req.assignedWorker || "Unassigned";
			if (!name || name === "Unassigned") continue;
			if (!byName.has(name)) {
				byName.set(name, {
					id: `worker-${idCounter++}`,
					name,
					organization: req.assignedWorkerOrg,
					activeRequestsCount: 0,
					status: "Active",
				});
			}
			const w = byName.get(name)!;
			w.activeRequestsCount = (w.activeRequestsCount ?? 0) + 1;
		}
		let workers = Array.from(byName.values());
		if (workers.length === 0) {
			workers = [
				{
					id: "worker-1",
					name: "ABC Diamond Technicians",
					organization: "ABC Diamond",
					activeRequestsCount: 0,
					status: "Active",
				},
				{
					id: "worker-2",
					name: "Maintenance Team",
					organization: "Property Mgmt",
					activeRequestsCount: 0,
					status: "Active",
				},
			];
		}
		return workers;
	} catch (error) {
		console.error("Error fetching maintenance workers:", error);
		return [
			{
				id: "worker-1",
				name: "ABC Diamond Technicians",
				organization: "ABC Diamond",
				status: "Active",
			},
			{ id: "worker-2", name: "Maintenance Team", organization: "Property Mgmt", status: "Active" },
		];
	}
}
