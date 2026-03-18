# Geocoding — Implementation Guide

## What is geocoding

Geocoding converts a human-readable address (e.g. "123 Main St, San Francisco, CA") into latitude/longitude coordinates for map display.

---

## Recommended service: OpenStreetMap Nominatim

| Property | Value |
|----------|-------|
| Endpoint | `https://nominatim.openstreetmap.org/search` |
| Cost | Free |
| API key | None |
| Rate limit | 1 request/second (enforced by Nominatim usage policy) |
| Terms | Must set a meaningful `User-Agent` header |

---

## Geocode utility with caching and concurrency control

Create at `utils/geocode.ts`:

```ts
const CACHE = new Map<string, { lat: number; lng: number }>();
const MAX_CONCURRENT = 6;
let inFlight = 0;
const queue: Array<() => void> = [];

function acquire(): Promise<void> {
  if (inFlight < MAX_CONCURRENT) {
    inFlight += 1;
    return Promise.resolve();
  }
  return new Promise<void>((resolve) => {
    queue.push(() => {
      inFlight += 1;
      resolve();
    });
  });
}

function release(): void {
  inFlight -= 1;
  const next = queue.shift();
  if (next) next();
}

export interface GeocodeResult {
  lat: number;
  lng: number;
}

export async function geocodeAddress(address: string): Promise<GeocodeResult | null> {
  const key = address.trim().replace(/\s+/g, " ").toLowerCase();
  if (!key) return null;
  const cached = CACHE.get(key);
  if (cached) return cached;

  await acquire();
  try {
    const url = new URL("https://nominatim.openstreetmap.org/search");
    url.searchParams.set("q", address.trim());
    url.searchParams.set("format", "json");
    url.searchParams.set("limit", "1");
    const res = await fetch(url.toString(), {
      headers: { "User-Agent": "MyApp/1.0 (contact@example.com)" },
    });
    if (!res.ok) return null;
    const data = (await res.json()) as Array<{ lat?: string; lon?: string }>;
    const first = data?.[0];
    if (!first?.lat || !first?.lon) return null;
    const lat = Number(first.lat);
    const lng = Number(first.lon);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return null;
    const result = { lat, lng };
    CACHE.set(key, result);
    return result;
  } catch {
    return null;
  } finally {
    release();
  }
}
```

### Design decisions

| Decision | Rationale |
|----------|-----------|
| In-memory cache | Avoids repeated API calls for the same address within a session |
| Concurrency limiter (6) | Prevents flooding Nominatim when geocoding many addresses in parallel |
| Semaphore queue | Requests beyond the limit wait in FIFO order |
| Null return on failure | Callers decide how to handle missing coordinates (skip marker, show fallback) |
| `User-Agent` header | Required by Nominatim usage policy; set to your app name and contact |

---

## React hook: useGeocode

For single-address geocoding (e.g. detail pages):

```ts
import { useState, useEffect } from "react";
import { geocodeAddress, type GeocodeResult } from "@/utils/geocode";

export function useGeocode(address: string | null | undefined): {
  coords: GeocodeResult | null;
  loading: boolean;
} {
  const [coords, setCoords] = useState<GeocodeResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!address?.trim()) {
      setCoords(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    geocodeAddress(address)
      .then((result) => {
        if (!cancelled) setCoords(result);
      })
      .catch(() => {
        if (!cancelled) setCoords(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [address?.trim() ?? ""]);

  return { coords, loading };
}
```

### Usage in a component

```tsx
const { coords } = useGeocode("123 Main St, San Francisco, CA");

{coords && (
  <MapView
    center={[coords.lat, coords.lng]}
    zoom={15}
    markers={[{ lat: coords.lat, lng: coords.lng, label: "Location" }]}
  />
)}
```

---

## Batch geocoding for lists

When geocoding multiple addresses (e.g. search results → map markers), use `Promise.all` with the built-in concurrency limiter:

```ts
const results = await Promise.all(
  addresses.map(({ id, address }) =>
    geocodeAddress(address).then((coords) =>
      coords ? { id, lat: coords.lat, lng: coords.lng } : null
    )
  )
);
const markers = results.filter(Boolean);
```

The `MAX_CONCURRENT` semaphore in the utility ensures no more than 6 requests are in flight, even if you pass 50 addresses.

---

## Hook for multi-marker geocoding

```ts
import { useState, useEffect } from "react";
import { geocodeAddress } from "@/utils/geocode";
import type { MapMarker } from "@/components/MapView";

export function useMapMarkers(
  items: Array<{ id: string; address: string; label?: string }>
): { markers: MapMarker[]; loading: boolean } {
  const [markers, setMarkers] = useState<MapMarker[]>([]);
  const [loading, setLoading] = useState(false);

  const key = items.map((i) => i.id).join(",");

  useEffect(() => {
    if (items.length === 0) {
      setMarkers([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all(
      items.map((item) =>
        geocodeAddress(item.address).then((coords) =>
          coords ? { lat: coords.lat, lng: coords.lng, label: item.label ?? item.address } : null
        )
      )
    )
      .then((results) => {
        if (!cancelled) setMarkers(results.filter(Boolean) as MapMarker[]);
      })
      .catch(() => {
        if (!cancelled) setMarkers([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [key]);

  return { markers, loading };
}
```

---

## CSP considerations

If CSP is enforced, add Nominatim to `connect-src`:

```
connect-src 'self' https://nominatim.openstreetmap.org;
```

---

## Alternative geocoding providers

| Provider | Free tier | API key | Notes |
|----------|-----------|---------|-------|
| Nominatim (OSM) | Unlimited (rate-limited) | No | Best for prototypes and low-traffic apps |
| Google Geocoding API | 200 USD/month credit | Yes | Most accurate; requires billing account |
| Mapbox Geocoding | 100K req/month | Yes | Good accuracy; JS SDK available |
| LocationIQ | 5K req/day | Yes | Nominatim-compatible API |

For production apps with high traffic, consider Google or Mapbox with an API key and server-side geocoding.
