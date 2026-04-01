import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "@/features/authentication/context/AuthContext";
import { ROUTES } from "@/features/authentication/authenticationConfig";
import { useTenantAccess } from "@/context/TenantAccessContext";

export default function TenantRoute() {
	const location = useLocation();
	const { isAuthenticated, loading } = useAuth();
	const { hasTenantRecord, loading: tenantLoading } = useTenantAccess();

	if (loading || tenantLoading) return null;

	if (!isAuthenticated) {
		return <Navigate to={ROUTES.LOGIN.PATH} state={{ from: location.pathname }} replace />;
	}

	if (!hasTenantRecord) {
		return <Navigate to="/" replace />;
	}

	return <Outlet />;
}
