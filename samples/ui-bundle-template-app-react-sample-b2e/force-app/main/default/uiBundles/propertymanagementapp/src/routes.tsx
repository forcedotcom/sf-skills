import type { RouteObject } from 'react-router';
import AppLayout from './appLayout';
import Home from './pages/Home';
import NotFound from './pages/NotFound';
import TestAccPage from "./pages/TestAccPage";
import { Navigate } from "react-router";
import PropertySearch from "./pages/PropertySearch";
import MaintenanceRequestSearch from "./pages/MaintenanceRequestSearch";
import MaintenanceWorkerSearch from "./pages/MaintenanceWorkerSearch";
import ApplicationSearch from "./pages/ApplicationSearch";
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
        path: "maintenance",
        children: [
          {
            index: true,
            element: <Navigate to={PATHS.MAINTENANCE_REQUESTS} replace />
          },
          {
            path: "requests",
            element: <MaintenanceRequestSearch />,
            handle: { showInNavigation: true, label: "Maintenance Requests" }
          },
          {
            path: "workers",
            element: <MaintenanceWorkerSearch />,
            handle: { showInNavigation: true, label: "Maintenance Workers" }
          }
        ]
      },
      {
        path: "properties",
        element: <PropertySearch />,
        handle: { showInNavigation: true, label: "Properties" }
      },
      {
        path: "applications",
        element: <ApplicationSearch />,
        handle: { showInNavigation: true, label: "Applications" }
      }
    ]
  }
];
