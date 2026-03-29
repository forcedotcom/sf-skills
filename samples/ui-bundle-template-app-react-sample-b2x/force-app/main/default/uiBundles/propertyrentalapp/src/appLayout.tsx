import { useState } from "react";
import { Outlet } from "react-router";
import { TopBar } from "@/components/layout/TopBar";
import { NavMenu } from "@/components/layout/VerticalNav";
import { Toaster } from "@/components/ui/sonner";

export default function AppLayout() {
	const [isNavOpen, setIsNavOpen] = useState(false);

	return (
		<div className="flex min-h-screen flex-col bg-gray-50">
			<Toaster />
			<TopBar onMenuClick={() => setIsNavOpen(true)} />

			<div className="flex flex-1 overflow-hidden">
				<NavMenu isOpen={isNavOpen} onClose={() => setIsNavOpen(false)} />

				<main className="flex-1 overflow-auto bg-gray-50 p-4 md:p-8" role="main">
					<Outlet />
				</main>
			</div>
		</div>
	);
}
