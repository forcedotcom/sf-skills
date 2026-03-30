import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getCurrentUser } from "@salesforce/webapp-experimental/api";
import { API_ROUTES } from "../authenticationConfig";

interface User {
	readonly id: string;
	readonly name: string;
}

interface AuthContextType {
	user: User | null;
	isAuthenticated: boolean;
	loading: boolean;
	error: string | null;
	checkAuth: () => Promise<void>;
	logout: (startURL?: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
	children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
	const [user, setUser] = useState<User | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const checkAuth = useCallback(async () => {
		setLoading(true);
		setError(null);

		try {
			const userData = await getCurrentUser();
			setUser(userData);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : "Authentication failed";
			setError(errorMessage);
			setUser(null);
		} finally {
			setLoading(false);
		}
	}, []);

	const logout = useCallback((startURL?: string) => {
		// Navigate to logout URL (server-side endpoint)
		// Use replace to prevent back button from returning to authenticated session
		const finalLogoutUrl = startURL
			? `${API_ROUTES.LOGOUT}?startURL=${encodeURIComponent(startURL)}`
			: API_ROUTES.LOGOUT;
		window.location.replace(finalLogoutUrl);
	}, []);

	useEffect(() => {
		checkAuth();
	}, [checkAuth]);

	const value: AuthContextType = {
		user,
		isAuthenticated: user !== null,
		loading,
		error,
		checkAuth,
		logout,
	};

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access the authentication context.
 * @returns {AuthContextType} Authentication state (user, isAuthenticated, loading, error, checkAuth)
 * @throws {Error} If used outside of an AuthProvider
 */
export function useAuth(): AuthContextType {
	const context = useContext(AuthContext);
	if (context === undefined) {
		throw new Error("useAuth must be used within an AuthProvider");
	}
	return context;
}

/**
 * Returns the current authenticated user.
 * @returns {User} The authenticated user object
 * @throws {Error} If not used within AuthProvider or user is not authenticated
 */
export function getUser(): User {
	const context = useAuth();
	if (!context.user) {
		throw new Error("Authenticated context not established");
	}
	return context.user;
}
