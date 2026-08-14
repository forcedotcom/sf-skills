import { createBrowserRouter, RouterProvider } from "react-router";
import { routes } from "@/routes";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import "./styles/global.css";

// Normalize basename: strip trailing slash so it matches URLs like /lwr/application/ai/c-app
const rawBasePath = (globalThis as any).SFDC_ENV?.basePath;
const basename = typeof rawBasePath === "string" ? rawBasePath.replace(/\/+$/, "") : undefined;
const router = createBrowserRouter(routes, { basename });
const rootEl = document.getElementById("root");
if (rootEl) {
	createRoot(rootEl).render(
		<StrictMode>
			<ErrorBoundary>
				<RouterProvider router={router} />
			</ErrorBoundary>
		</StrictMode>,
	);
}
