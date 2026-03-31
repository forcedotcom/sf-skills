import { useEffect, useState } from "react";
import { hasTenantAccess } from "@/api/tenantApi";

export function useTenantAccess(userId: string | undefined): {
	hasTenantRecord: boolean;
	loading: boolean;
} {
	const [hasTenantRecord, setHasTenantRecord] = useState(false);
	const [loading, setLoading] = useState(false);

	useEffect(() => {
		const id = userId?.trim() ?? "";
		if (!id) {
			setHasTenantRecord(false);
			setLoading(false);
			return;
		}

		let cancelled = false;
		setLoading(true);
		hasTenantAccess(id)
			.then((allowed) => {
				if (!cancelled) setHasTenantRecord(allowed);
			})
			.catch(() => {
				if (!cancelled) setHasTenantRecord(false);
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});

		return () => {
			cancelled = true;
		};
	}, [userId]);

	return { hasTenantRecord, loading };
}
