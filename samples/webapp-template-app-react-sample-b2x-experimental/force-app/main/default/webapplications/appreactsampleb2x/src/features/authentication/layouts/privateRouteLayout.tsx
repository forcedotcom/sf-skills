import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../context/AuthContext";
import { AUTH_REDIRECT_PARAM, ROUTES } from "../authenticationConfig";
import { CardSkeleton } from "../layout/card-skeleton";

export interface PrivateRouteProps {
	/**
	 * Whether to show a card skeleton placeholder while authentication is loading.
	 * @default false
	 */
	showCardSkeleton?: boolean;
}

/**
 * [Dev Note] Route Guard:
 * Renders the child route (Outlet) if the user is authenticated.
 * Otherwise, redirects to Login with a 'startUrl' parameter so the user can be
 * returned to this page after successful login.
 */
export default function PrivateRoute({ showCardSkeleton = false }: PrivateRouteProps) {
	const { isAuthenticated, loading } = useAuth();
	const location = useLocation();

	if (loading) return showCardSkeleton ? <CardSkeleton contentMaxWidth="md" /> : null;

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
