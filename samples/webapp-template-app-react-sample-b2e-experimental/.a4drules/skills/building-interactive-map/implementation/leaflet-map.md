# Leaflet Map — Implementation Guide

## Dependencies

Add to the project:

```bash
npm install leaflet react-leaflet
npm install -D @types/leaflet
```

Import the Leaflet CSS in the component file (not in global CSS — keeps it co-located):

```tsx
import "leaflet/dist/leaflet.css";
```

---

## TypeScript declaration (if @types/leaflet is unavailable)

If the project cannot install `@types/leaflet`, create a declaration file:

```ts
// types/leaflet.d.ts
declare module "leaflet" {
  const L: unknown;
  export default L;
}
declare module "leaflet/dist/leaflet.css";
```

---

## Reusable map component

Create a generic map component at `components/MapView.tsx` (or similar):

```tsx
import { useMemo, useState, useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const Leaflet = L as {
  divIcon: (opts: {
    className?: string;
    html?: string;
    iconSize?: [number, number];
    iconAnchor?: [number, number];
    popupAnchor?: [number, number];
  }) => unknown;
};

const pinIcon = Leaflet.divIcon({
  className: "map-pin",
  html: `<span class="map-pin-shape" aria-hidden="true"></span>`,
  iconSize: [28, 40],
  iconAnchor: [14, 40],
  popupAnchor: [0, -40],
});

export interface MapMarker {
  lat: number;
  lng: number;
  label?: string;
}

interface MapViewProps {
  center: [number, number];
  zoom?: number;
  markers?: MapMarker[];
  className?: string;
}

function MapCenterUpdater({ center, zoom = 13 }: { center: [number, number]; zoom?: number }) {
  const map = useMap() as { setView: (center: [number, number], zoom: number) => void };
  useEffect(() => {
    map.setView(center, zoom);
  }, [map, center[0], center[1], zoom]);
  return null;
}

export default function MapView({
  center,
  zoom = 13,
  markers = [],
  className = "h-[400px] w-full rounded-xl overflow-hidden",
}: MapViewProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const effectiveCenter = useMemo((): [number, number] => {
    if (markers.length > 0) {
      const sum = markers.reduce((acc, m) => [acc[0] + m.lat, acc[1] + m.lng], [0, 0]);
      return [sum[0] / markers.length, sum[1] / markers.length];
    }
    return center;
  }, [center, markers]);

  if (!mounted || typeof window === "undefined") {
    return (
      <div
        className={className + " bg-muted flex items-center justify-center text-muted-foreground text-sm"}
        aria-hidden
      >
        Loading map…
      </div>
    );
  }

  return (
    <div className={className} aria-label="Map">
      <MapContainer
        center={effectiveCenter}
        zoom={zoom}
        scrollWheelZoom
        className="h-full w-full"
        style={{ minHeight: 200 }}
      >
        <MapCenterUpdater center={effectiveCenter} zoom={zoom} />
        <TileLayer
          attribution='Data by &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        {markers.map((m, i) => (
          <Marker key={`${m.lat}-${m.lng}-${i}`} position={[m.lat, m.lng]} icon={pinIcon}>
            <Popup>{m.label ?? "Location"}</Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
```

---

## Tile provider: OpenStreetMap

The default tile URL is free and requires no API key:

```
https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

| Property | Value |
|----------|-------|
| Cost | Free |
| API key | None |
| Max zoom | 19 |
| Attribution | Required — `© OpenStreetMap` |

CSP `img-src` must include `https://tile.openstreetmap.org` if CSP is enforced.

---

## Custom pin icon via CSS

The `divIcon` approach avoids external marker image dependencies. Add these styles to your global CSS or a co-located CSS file:

```css
.map-pin {
  background: transparent !important;
  border: none !important;
}

.map-pin-shape {
  display: block;
  width: 28px;
  height: 40px;
  background: hsl(var(--primary));
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.map-pin-shape::after {
  content: "";
  display: block;
  width: 12px;
  height: 12px;
  background: white;
  border-radius: 50%;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
```

---

## SSR safety

Leaflet requires `window` and `document`. The component guards against SSR with:

1. A `mounted` state that only becomes `true` in `useEffect` (client-side).
2. A `typeof window === "undefined"` check.
3. A loading placeholder rendered during SSR / before mount.

This prevents "window is not defined" errors in SSR or static builds.

---

## MapCenterUpdater pattern

`react-leaflet`'s `MapContainer` does not re-center when the `center` prop changes after initial render. The `MapCenterUpdater` child component uses `useMap()` to call `map.setView()` reactively:

```tsx
function MapCenterUpdater({ center, zoom = 13 }: { center: [number, number]; zoom?: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [map, center[0], center[1], zoom]);
  return null;
}
```

Place it as a direct child of `<MapContainer>`.

---

## Multi-marker center calculation

When rendering multiple markers, auto-center the map on their centroid:

```tsx
const effectiveCenter = useMemo((): [number, number] => {
  if (markers.length > 0) {
    const sum = markers.reduce((acc, m) => [acc[0] + m.lat, acc[1] + m.lng], [0, 0]);
    return [sum[0] / markers.length, sum[1] / markers.length];
  }
  return fallbackCenter;
}, [markers, fallbackCenter]);
```

---

## Split-panel layout (map + list)

For a search page with map on the left and scrollable results on the right:

```tsx
<div className="flex h-[calc(100vh-4rem)] min-h-[500px] flex-col">
  {/* Search bar */}
  <div className="shrink-0 border-b bg-background px-4 py-3">
    {/* search input */}
  </div>
  {/* Map + List */}
  <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
    <div className="h-64 shrink-0 lg:h-full lg:min-h-0 lg:w-2/3" aria-label="Map">
      <MapView center={center} markers={markers} className="h-full w-full" />
    </div>
    <aside className="flex w-full flex-col border-t lg:w-1/3 lg:border-l lg:border-t-0">
      <div className="flex-1 overflow-y-auto p-4">
        {/* list items */}
      </div>
    </aside>
  </div>
</div>
```

Key points:
- `h-[calc(100vh-4rem)]` fills viewport minus header.
- `lg:flex-row` stacks vertically on mobile, side-by-side on desktop.
- List panel uses `overflow-y-auto` for independent scrolling.

---

## Accessibility

- Wrap the map `<div>` with `aria-label="Map"` or a descriptive label.
- Pin icon inner HTML uses `aria-hidden="true"`.
- Popups contain text labels for each marker.
- Provide a text-based alternative (address list) for screen readers.
