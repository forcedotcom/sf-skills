import { Outlet } from "react-router";
import { TopBar } from "@/components/TopBar";
import { NavMenu } from "@/components/NavMenu";

export default function AppLayout() {
	return (
		<div className="flex h-screen flex-col">
			<TopBar />

			<div className="flex flex-1 overflow-hidden">
				<NavMenu />

				<main className="flex-1 overflow-auto bg-gray-50 p-8" role="main">
					<Outlet />
				</main>
			</div>
		</div>
	);
}
