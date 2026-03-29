import type { RouteObject } from 'react-router';
import { routes } from './routes';

export type RouteWithFullPath = RouteObject & { fullPath: string };

const flatMapRoutes = (
  route: RouteObject,
  parentPath: string = ''
): RouteWithFullPath[] => {
  let fullPath: string;

  if (route.index) {
    fullPath = parentPath || '/';
  } else if (route.path) {
    if (route.path.startsWith('/')) {
      fullPath = route.path;
    } else {
      fullPath =
        parentPath === '/' ? `/${route.path}` : `${parentPath}/${route.path}`;
    }
  } else {
    fullPath = parentPath;
  }

  const routeWithPath = { ...route, fullPath };

  const childRoutes =
    route.children?.flatMap(child => flatMapRoutes(child, fullPath)) || [];

  return [routeWithPath, ...childRoutes];
};

export const getAllRoutes = (): RouteWithFullPath[] => {
  return routes.flatMap(route => flatMapRoutes(route));
};
