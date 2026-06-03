import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/features/authentication/context/AuthContext";
import { getTenantProperties, type TenantProperty } from "@/api/tenants/tenantApi";

interface TenantAccessContextType {
	hasTenantRecord: boolean;
	tenantProperties: TenantProperty[];
	loading: boolean;
}

const TenantAccessContext = createContext<TenantAccessContextType>({
	hasTenantRecord: false,
	tenantProperties: [],
	loading: true,
});

export function TenantAccessProvider({ children }: { children: ReactNode }) {
	const { user } = useAuth();
	const [tenantProperties, setTenantProperties] = useState<TenantProperty[]>([]);
	const [loading, setLoading] = useState(true);

	// Reset state synchronously during render when user changes
	const [prevUserId, setPrevUserId] = useState(user?.id);
	if (prevUserId !== user?.id) {
		setPrevUserId(user?.id);
		const id = user?.id?.trim() ?? "";
		if (!id) {
			if (tenantProperties.length > 0) setTenantProperties([]);
			if (loading) setLoading(false);
		} else {
			if (!loading) setLoading(true);
		}
	}

	useEffect(() => {
		const id = user?.id?.trim() ?? "";
		if (!id) return;

		let cancelled = false;
		getTenantProperties(id)
			.then((props) => {
				if (!cancelled) setTenantProperties(props);
			})
			.catch(() => {
				if (!cancelled) setTenantProperties([]);
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});

		return () => {
			cancelled = true;
		};
	}, [user?.id]);

	const hasTenantRecord = tenantProperties.length > 0;

	return (
		<TenantAccessContext.Provider value={{ hasTenantRecord, tenantProperties, loading }}>
			{children}
		</TenantAccessContext.Provider>
	);
}

export function useTenantAccess(): TenantAccessContextType {
	return useContext(TenantAccessContext);
}
