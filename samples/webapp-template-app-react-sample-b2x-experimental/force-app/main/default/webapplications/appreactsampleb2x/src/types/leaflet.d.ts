/**
 * Type declarations for leaflet and react-leaflet when types are not installed in the type-check context.
 * The app lists these in feature packageJson; this file satisfies TypeScript during source builds.
 */
declare module "leaflet" {
	const L: Record<string, unknown>;
	export default L;
}

declare module "react-leaflet" {
	import type { ComponentType } from "react";
	export const MapContainer: ComponentType<Record<string, unknown>>;
	export const TileLayer: ComponentType<Record<string, unknown>>;
	export const Marker: ComponentType<Record<string, unknown>>;
	export const Popup: ComponentType<Record<string, unknown>>;
	export function useMap(): Record<string, unknown>;
}
