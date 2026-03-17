---
name: salesforce-webapp-react-weather-widget
description: Adds a weather widget to React pages using the free Open-Meteo API. Use when the user asks to add weather, show a forecast, display current conditions, add a weather card, or integrate weather data into the web application.
---

# Weather Widget

## When to Use

Use this skill when:
- Adding current weather conditions to a dashboard or sidebar
- Displaying an hourly or daily forecast
- Showing location-based weather for a property, event, or destination

---

## Step 1 — Determine widget scope

Identify what weather data the user needs:

- **Current conditions only** — temperature, description, wind, humidity
- **Current + hourly forecast** — conditions + next 6–12 hours
- **Current + daily forecast** — conditions + multi-day outlook

If unclear, ask:

> "Should the weather widget show just current conditions, or include an hourly/daily forecast too?"

---

## Step 2 — Determine location source

The widget needs a latitude/longitude. Identify where this comes from:

- **Fixed default** — hardcoded city (e.g. San Francisco: `37.7749, -122.4194`)
- **User's location** — browser Geolocation API
- **Address-based** — geocode an address to lat/lng (see the `webapp-react-interactive-map` skill for geocoding)
- **Prop-driven** — parent component passes lat/lng

---

## Step 3 — Implementation

Read the corresponding guides:

- **Weather data hook** — read `implementation/weather-hook.md` for the `useWeather` custom hook and Open-Meteo API integration.
- **Weather UI component** — read `implementation/weather-ui.md` for rendering weather data in a card.

---

## Verification

Before completing:

1. Widget shows real weather data (not mocked).
2. Loading and error states are handled gracefully.
3. Temperature displays in the correct unit (°F or °C).
4. Run from the web app directory:

```bash
cd force-app/main/default/webapplications/<appName> && npm run lint && npm run build
```

- **Lint:** MUST result in 0 errors.
- **Build:** MUST succeed.
