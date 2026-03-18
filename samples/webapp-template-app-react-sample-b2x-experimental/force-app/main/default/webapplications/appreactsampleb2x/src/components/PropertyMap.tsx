/**
 * Leaflet map for property search and detail. Uses OpenStreetMap tiles (no API key).
 * Renders one pin per property (each marker in the markers array).
 */
import { useMemo, useState, useEffect, type ReactNode } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Type for leaflet L when using declaration-only (no @types/leaflet)
const Leaflet = L as {
	divIcon: (opts: {
		className?: string;
		html?: string;
		iconSize?: [number, number];
		iconAnchor?: [number, number];
		popupAnchor?: [number, number];
	}) => unknown;
};

// Lucide-style map pin (teardrop + circle), filled, 1.5x size
const PIN_SVG =
	'<svg xmlns="http://www.w3.org/2000/svg" width="42" height="60" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" fill="currentColor"/><circle cx="12" cy="10" r="3" fill="white" stroke="none"/></svg>';

const pinIcon = Leaflet.divIcon({
	className: "property-map-pin",
	html: PIN_SVG,
	iconSize: [42, 60],
	iconAnchor: [21, 60],
	popupAnchor: [0, -60],
});

export interface MapMarker {
	lat: number;
	lng: number;
	label?: string;
	/** Property__c id; used to look up listing record for popup card */
	propertyId?: string;
}

/** Bounding box in lat/lng (Leaflet getBounds()). */
export interface MapBounds {
	north: number;
	south: number;
	east: number;
	west: number;
}

interface PropertyMapProps {
	/** Center [lat, lng] */
	center: [number, number];
	/** Initial zoom 1–18 */
	zoom?: number;
	/** Optional markers */
	markers?: MapMarker[];
	/** Optional: render custom content in each marker popup (e.g. PropertyListingCard) */
	popupContent?: (marker: MapMarker) => ReactNode;
	/** Called when the user pans or zooms; use to filter list by visible pins */
	onBoundsChange?: (bounds: MapBounds | null) => void;
	/** CSS class for the container (e.g. height) */
	className?: string;
}

function MapCenterUpdater({ center, zoom = 13 }: { center: [number, number]; zoom?: number }) {
	const map = useMap() as { setView: (center: [number, number], zoom: number) => void };
	useEffect(() => {
		map.setView(center, zoom);
	}, [map, center[0], center[1], zoom]);
	return null;
}

function MapBoundsReporter({
	onBoundsChange,
}: {
	onBoundsChange?: (bounds: MapBounds | null) => void;
}) {
	const map = useMap() as {
		getBounds?: () => {
			getNorth: () => number;
			getSouth: () => number;
			getEast: () => number;
			getWest: () => number;
		};
		on?: (event: string, fn: () => void) => void;
		off?: (event: string, fn: () => void) => void;
	};
	useEffect(() => {
		if (!onBoundsChange || !map.getBounds) return;
		const report = () => {
			const b = map.getBounds!();
			onBoundsChange({
				north: b.getNorth(),
				south: b.getSouth(),
				east: b.getEast(),
				west: b.getWest(),
			});
		};
		// Only report on moveend (user pan/zoom). Reporting on mount caused setState -> re-render -> map setView -> moveend -> loop.
		map.on?.("moveend", report);
		return () => {
			map.off?.("moveend", report);
		};
	}, [map, onBoundsChange]);
	return null;
}

/** Wraps popup content with an in-card close button and shadow; removes need for Leaflet's default chrome */
function PopupContentWrapper({ children }: { children: ReactNode }) {
	const map = useMap() as { closePopup?: () => void };
	return (
		<div className="relative min-w-0">
			<button
				type="button"
				onClick={() => map.closePopup?.()}
				className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white transition-colors hover:bg-black/80"
				aria-label="Close"
			>
				×
			</button>
			<div className="rounded-2xl shadow-lg overflow-hidden">{children}</div>
		</div>
	);
}

export default function PropertyMap({
	center,
	zoom = 13,
	markers = [],
	popupContent,
	onBoundsChange,
	className = "h-[400px] w-full rounded-xl overflow-hidden",
}: PropertyMapProps) {
	const [mounted, setMounted] = useState(false);
	useEffect(() => {
		setMounted(true);
	}, []);

	const hasMarkers = markers.length > 0;
	const effectiveCenter = useMemo((): [number, number] => {
		if (hasMarkers) {
			return [markers[0].lat, markers[0].lng];
		}
		return center;
	}, [center, hasMarkers, markers]);

	if (!mounted || typeof window === "undefined") {
		return (
			<div
				className={
					className + " bg-muted flex items-center justify-center text-muted-foreground text-sm"
				}
				aria-hidden
			>
				Loading map…
			</div>
		);
	}

	return (
		<div className={className} aria-label="Property map">
			<MapContainer
				center={effectiveCenter}
				zoom={zoom}
				scrollWheelZoom
				className="h-full w-full"
				style={{ minHeight: 200 }}
			>
				<MapCenterUpdater center={effectiveCenter} zoom={zoom} />
				<MapBoundsReporter onBoundsChange={onBoundsChange} />
				<TileLayer
					attribution='&copy; <a href="https://leafletjs.com/">Leaflet</a> | Data by &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
					url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
					maxZoom={19}
				/>
				{markers.map((m, i) => (
					<Marker
						key={`${m.lat}-${m.lng}-${m.propertyId ?? i}`}
						position={[m.lat, m.lng]}
						icon={pinIcon}
					>
						<Popup>
							{popupContent ? (
								<PopupContentWrapper>{popupContent(m)}</PopupContentWrapper>
							) : (
								(m.label ?? "Property")
							)}
						</Popup>
					</Marker>
				))}
			</MapContainer>
		</div>
	);
}
