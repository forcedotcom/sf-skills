import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../context/AuthContext";
import { AUTH_REDIRECT_PARAM, ROUTES } from "../authenticationConfig";
import { CardSkeleton } from "../layout/card-skeleton";

/**
 * [Dev Note] Route Guard:
 * Renders the child route (Outlet) if the user is authenticated.
 * Otherwise, redirects to Login with a 'startUrl' parameter so the user can be
 * returned to this page after successful login.
 */
export default function PrivateRoute() {
	const { isAuthenticated, loading } = useAuth();
	const location = useLocation();

	if (loading) return <CardSkeleton contentMaxWidth="md" />;

	if (!isAuthenticated) {
		const searchParams = new URLSearchParams();

		// [Dev Note] Capture current location to return after login
		const destination = location.pathname + location.search;
		searchParams.set(AUTH_REDIRECT_PARAM, destination);
		return (
			<Navigate // Navigate accepts an object to safely construct the URL
				to={{
					pathname: ROUTES.LOGIN.PATH,
					search: searchParams.toString(),
				}}
				replace
			/>
		);
	}

	return <Outlet />;
}
