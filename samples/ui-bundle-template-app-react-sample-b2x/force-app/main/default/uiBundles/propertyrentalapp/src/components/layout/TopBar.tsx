import { ChevronDown, Menu, User } from "lucide-react";
import { Link } from "react-router";
import { ROUTES } from "@/features/authentication/authenticationConfig";
import zenLogo from "@/assets/icons/zen-logo.svg";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { AuthMenu } from "@/features/authentication/menu/AuthMenu";

export interface TopBarProps {
	onMenuClick?: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
	return (
		<header className="flex h-16 items-center justify-between bg-teal-700 px-6 text-white">
			<div className="flex items-center gap-4">
				<Button
					variant="ghost"
					size="icon"
					onClick={onMenuClick}
					className="text-white hover:bg-teal-600 md:hidden"
					aria-label="Toggle menu"
				>
					<Menu className="size-6" />
				</Button>
				<Logo />
			</div>

			<AuthMenu
				trigger={(user) => (
					<Button
						variant="ghost"
						className="h-10 gap-2 rounded-lg px-3 text-base text-white hover:bg-teal-600 hover:text-white"
						aria-label="User menu"
					>
						<Avatar className="size-7 bg-teal-300 text-teal-900">
							<AvatarFallback className="bg-teal-300 font-semibold text-teal-900">
								{user.name.charAt(0).toUpperCase()}
							</AvatarFallback>
						</Avatar>
						<span className="hidden font-medium md:inline">{user.name.toUpperCase()}</span>
						<ChevronDown className="hidden size-4 md:block" />
					</Button>
				)}
				guestContent={
					<Button
						asChild
						variant="secondary"
						size="icon"
						className="rounded-full bg-white text-teal-700 hover:bg-teal-50 md:h-9 md:w-auto md:gap-2 md:rounded-lg md:px-4"
					>
						<Link to={ROUTES.LOGIN.PATH}>
							<User className="size-5 md:size-4" />
							<span className="hidden md:inline">Sign Up / Sign In</span>
						</Link>
					</Button>
				}
			/>
		</header>
	);
}

function Logo() {
	return (
		<div className="flex items-center gap-2">
			<img src={zenLogo} alt="Zenlease Logo" className="size-8" />
			<span className="text-xl tracking-wide">
				<span className="font-light">ZEN</span>
				<span className="font-semibold">LEASE</span>
			</span>
		</div>
	);
}
