import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/features/authentication/context/AuthContext";
import { hasTenantAccess } from "@/api/tenantApi";

interface TenantAccessContextType {
	hasTenantRecord: boolean;
	loading: boolean;
}

const TenantAccessContext = createContext<TenantAccessContextType>({
	hasTenantRecord: false,
	loading: true,
});

export function TenantAccessProvider({ children }: { children: ReactNode }) {
	const { user } = useAuth();
	const [hasTenantRecord, setHasTenantRecord] = useState(false);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const id = user?.id?.trim() ?? "";
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
	}, [user?.id]);

	return (
		<TenantAccessContext.Provider value={{ hasTenantRecord, loading }}>
			{children}
		</TenantAccessContext.Provider>
	);
}

export function useTenantAccess(): TenantAccessContextType {
	return useContext(TenantAccessContext);
}
