import type { RouteObject } from 'react-router';
import Home from '@/pages/Home';
import NotFound from '@/pages/NotFound';
import AccountSearch from "./features/object-search/__examples__/pages/AccountSearch";
import AccountObjectDetail from "./features/object-search/__examples__/pages/AccountObjectDetailPage";
import AuthAppLayout from "./features/authentication/layouts/AuthAppLayout";
import Login from "./features/authentication/pages/Login";
import Register from "./features/authentication/pages/Register";
import ForgotPassword from "./features/authentication/pages/ForgotPassword";
import ResetPassword from "./features/authentication/pages/ResetPassword";
import Profile from "./features/authentication/pages/Profile";
import ChangePassword from "./features/authentication/pages/ChangePassword";
import AuthenticationRoute from "./features/authentication/layouts/authenticationRouteLayout";
import PrivateRoute from "./features/authentication/layouts/privateRouteLayout";
import { ROUTES } from "./features/authentication/authenticationConfig";
import Dashboard from "@/pages/Dashboard";
import Maintenance from "@/pages/Maintenance";
import PropertySearch from "@/pages/PropertySearch";
import PropertyDetails from "@/pages/PropertyDetails";
import Application from "@/pages/Application";
import Contact from "@/pages/Contact";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <AuthAppLayout />,
    children: [
      {
        index: true,
        element: <Home />,
        handle: { showInNavigation: true, label: "Home" }
      },
      {
        path: "*",
        element: <NotFound />
      },
      {
        path: "accounts/:recordId",
        element: <AccountObjectDetail />
      },
      {
        path: "accounts",
        element: <AccountSearch />
      },
      {
        element: <AuthenticationRoute />,
        children: [
          {
            path: ROUTES.LOGIN.PATH,
            element: <Login />,
            handle: { showInNavigation: true, label: "Login", title: ROUTES.LOGIN.TITLE }
          },
          {
            path: ROUTES.REGISTER.PATH,
            element: <Register />,
            handle: { showInNavigation: false, title: ROUTES.REGISTER.TITLE }
          },
          {
            path: ROUTES.FORGOT_PASSWORD.PATH,
            element: <ForgotPassword />,
            handle: { showInNavigation: false, title: ROUTES.FORGOT_PASSWORD.TITLE }
          },
          {
            path: ROUTES.RESET_PASSWORD.PATH,
            element: <ResetPassword />,
            handle: { showInNavigation: false, title: ROUTES.RESET_PASSWORD.TITLE }
          }
        ]
      },
      {
        element: <PrivateRoute showCardSkeleton />,
        children: [
          {
            path: ROUTES.PROFILE.PATH,
            element: <Profile />,
            handle: { showInNavigation: true, label: "Profile", title: ROUTES.PROFILE.TITLE }
          },
          {
            path: ROUTES.CHANGE_PASSWORD.PATH,
            element: <ChangePassword />,
            handle: { showInNavigation: false, title: ROUTES.CHANGE_PASSWORD.TITLE }
          }
        ]
      },
      {
        path: "properties",
        element: <PropertySearch />,
        handle: { showInNavigation: true, label: "Property Search" }
      },
      {
        path: "property/:id",
        element: <PropertyDetails />
      },
      {
        path: "object/Property_Listing__c/:id",
        element: <PropertyDetails />
      },
      {
        path: "contact",
        element: <Contact />,
        handle: { showInNavigation: true, label: "Contact" }
      },
      {
        element: <PrivateRoute />,
        children: [
          {
            path: "dashboard",
            element: <Dashboard />,
            handle: { showInNavigation: true, label: "Dashboard" }
          },
          {
            path: "maintenance",
            element: <Maintenance />,
            handle: { showInNavigation: true, label: "Maintenance" }
          },
          {
            path: "application",
            element: <Application />
          }
        ]
      }
    ]
  }
];
