import { CircleUser, LogIn, LogOut, UserPen, UserPlus } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "../context/AuthContext";
import { ROUTES } from "../authenticationConfig";
import { Button } from "../../../components/ui/button";
import { Skeleton } from "../../../components/ui/skeleton";
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "../../../components/ui/dropdown-menu";

interface User {
	readonly id: string;
	readonly name: string;
}

export interface AuthMenuProps {
	/** Custom trigger button for the authenticated user's dropdown */
	trigger?: (user: User) => React.ReactNode;
	/** Content rendered instead of the dropdown when the user is not logged in (e.g. a standalone Sign In button) */
	guestContent?: React.ReactNode;
	/** Extra menu items inserted after "Edit Profile" and before "Sign Out" */
	menuItems?: React.ReactNode;
	/** CSS class applied to the DropdownMenuContent wrapper */
	className?: string;
}

export function AuthMenu({ trigger, guestContent, menuItems, className }: AuthMenuProps) {
	const { user, isAuthenticated, loading, logout } = useAuth();

	if (loading) {
		return <Skeleton className="size-8 rounded-full" />;
	}

	if (!isAuthenticated && guestContent) {
		return <>{guestContent}</>;
	}

	const defaultTrigger = (
		<Button variant="ghost" size="icon" aria-label="User menu">
			<CircleUser className="size-6" />
		</Button>
	);

	const triggerNode = (isAuthenticated && user && trigger?.(user)) || defaultTrigger;

	return (
		<DropdownMenu>
			<DropdownMenuTrigger asChild>{triggerNode}</DropdownMenuTrigger>

			<DropdownMenuContent align="end" className={className ?? "w-48"}>
				{isAuthenticated ? (
					<>
						<DropdownMenuLabel className="truncate">{user?.name}</DropdownMenuLabel>
						<DropdownMenuSeparator />
						<DropdownMenuItem asChild>
							<Link to={ROUTES.PROFILE.PATH}>
								<UserPen className="size-4" />
								Edit Profile
							</Link>
						</DropdownMenuItem>
						{menuItems}
						<DropdownMenuItem onClick={() => logout()}>
							<LogOut className="size-4" />
							Sign Out
						</DropdownMenuItem>
					</>
				) : (
					<>
						<DropdownMenuItem asChild>
							<Link to={ROUTES.LOGIN.PATH}>
								<LogIn className="size-4" />
								Log In
							</Link>
						</DropdownMenuItem>
						<DropdownMenuItem asChild>
							<Link to={ROUTES.REGISTER.PATH}>
								<UserPlus className="size-4" />
								Register
							</Link>
						</DropdownMenuItem>
					</>
				)}
			</DropdownMenuContent>
		</DropdownMenu>
	);
}

export default AuthMenu;
