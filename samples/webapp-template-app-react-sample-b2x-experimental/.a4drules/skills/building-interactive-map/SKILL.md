---
name: building-interactive-map
description: Adds interactive Leaflet maps with geocoded markers to React pages. Use when the user asks to add a map, show locations on a map, display property pins, add a map view, or integrate mapping into the web application.
---

# Interactive Map

## When to Use

Use this skill when:
- Adding an interactive map to a page (property search, store locator, location detail)
- Displaying one or more markers/pins on a map
- Converting addresses to map coordinates (geocoding)
- Building a split-panel layout with map + list

---

## Step 1 — Determine the map use case

Identify the scenario:

- **Multi-marker search** — map shows multiple pins alongside a scrollable list (e.g. property search, store locator)
- **Single-location detail** — map shows one pin for a specific address (e.g. property detail, contact page)
- **Static overview** — map centered on a region with no interactive markers

If unclear, ask:

> "Should the map show a single location, multiple markers from a list, or just a general area overview?"

---

## Step 2 — Install dependencies

The map requires `leaflet` and `react-leaflet`. Read `implementation/leaflet-map.md` for the exact dependency setup.

---

## Step 3 — Choose implementation path

Read the corresponding guide:

- **Map component** — read `implementation/leaflet-map.md` for building the reusable `<MapComponent>`.
- **Geocoding** — read `implementation/geocoding.md` for converting addresses to lat/lng coordinates.

For a multi-marker search page, you will need both.

---

## Step 4 — Wire the map into the page

Depending on the use case:

### Multi-marker search layout

```
┌──────────────────────────────────────┐
│  Search bar / filters                │
├────────────────────┬─────────────────┤
│                    │  Scrollable     │
│   Map (2/3)        │  list (1/3)     │
│                    │                 │
└────────────────────┴─────────────────┘
```

- Map takes `~2/3` width on desktop, full width on mobile stacked above the list.
- List is scrollable with `overflow-y-auto`.
- Markers are geocoded from addresses in the list.

### Single-location detail

- Place the map below the hero image or address section.
- Geocode the address on mount, render one marker.
- Show the map only after coordinates resolve (conditional render).

---

## Verification

Before completing:

1. Map renders with visible tiles (no gray boxes).
2. Markers appear at correct locations.
3. Map is responsive (works on mobile widths).
4. SSR-safe — no `window is not defined` errors during build.
5. Run from the web app directory:

```bash
cd force-app/main/default/webapplications/<appName> && npm run lint && npm run build
```

- **Lint:** MUST result in 0 errors.
- **Build:** MUST succeed.
