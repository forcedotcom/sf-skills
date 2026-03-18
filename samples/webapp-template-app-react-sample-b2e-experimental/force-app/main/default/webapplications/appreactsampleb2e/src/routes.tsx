import type { RouteObject } from 'react-router';
import AppLayout from './appLayout';
import Home from './pages/Home';
import NotFound from './pages/NotFound';
import TestAccPage from "./pages/TestAccPage";
import GlobalSearch from "./features/global-search/pages/GlobalSearch";
import DetailPage from "./features/global-search/pages/DetailPage";
import { Suspense } from "react";
import LoadingFallback from "./features/global-search/components/shared/LoadingFallback";
import { Navigate } from "react-router";
import Maintenance from "./pages/Maintenance";
import MaintenanceWorkers from "./pages/MaintenanceWorkers";
import Properties from "./pages/Properties";
import Applications from "./pages/Applications";
import { PATHS } from "./lib/routeConfig";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Home />,
        handle: { showInNavigation: true, label: "Home" }
      },
      {
        path: '*',
        element: <NotFound />
      },
      {
        path: "test-acc",
        element: <TestAccPage />,
        handle: { showInNavigation: true, label: "Test ACC" }
      },
      {
        path: "global-search/:query",
        element: (
					<Suspense fallback={<LoadingFallback />}>
						<GlobalSearch />
					</Suspense>
				),
        handle: { showInNavigation: false }
      },
      {
        path: "object/:objectApiName/:recordId",
        element: (
					<Suspense fallback={<LoadingFallback />}>
						<DetailPage />
					</Suspense>
				),
        handle: { showInNavigation: false }
      },
      {
        path: "maintenance",
        children: [
          {
            index: true,
            element: <Navigate to={PATHS.MAINTENANCE_REQUESTS} replace />
          },
          {
            path: "requests",
            element: <Maintenance />,
            handle: { showInNavigation: true, label: "Maintenance Requests" }
          },
          {
            path: "workers",
            element: <MaintenanceWorkers />,
            handle: { showInNavigation: true, label: "Maintenance Workers" }
          }
        ]
      },
      {
        path: "properties",
        element: <Properties />,
        handle: { showInNavigation: true, label: "Properties" }
      },
      {
        path: "applications",
        element: <Applications />,
        handle: { showInNavigation: true, label: "Applications" }
      }
    ]
  }
];
