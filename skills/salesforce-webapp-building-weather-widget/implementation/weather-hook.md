# Weather Hook — Implementation Guide

## Recommended API: Open-Meteo

| Property | Value |
|----------|-------|
| Endpoint | `https://api.open-meteo.com/v1/forecast` |
| Cost | Free for non-commercial use; no signup |
| API key | **None required** |
| Rate limit | 10,000 requests/day |
| Data | Current conditions, hourly, daily, historical |
| Weather codes | WMO standard codes |

### Why Open-Meteo over alternatives

| Provider | API key | Free tier | Notes |
|----------|---------|-----------|-------|
| **Open-Meteo** | No | 10K/day | Best for prototypes and low-traffic; no auth required |
| OpenWeatherMap | Yes | 1K calls/day | Popular but requires signup and API key |
| WeatherAPI.com | Yes | 1M calls/month | Good free tier but requires key management |
| Visual Crossing | Yes | 1K calls/day | Historical data strength |

Open-Meteo is the default choice because it requires zero configuration.

---

## WMO weather codes

Open-Meteo returns standard WMO weather codes. Map them to human-readable labels:

```ts
const WEATHER_LABELS: Record<number, string> = {
  0: "Clear",
  1: "Mainly clear",
  2: "Partly cloudy",
  3: "Overcast",
  45: "Foggy",
  48: "Depositing rime fog",
  51: "Light drizzle",
  53: "Drizzle",
  55: "Dense drizzle",
  61: "Slight rain",
  63: "Rain",
  65: "Heavy rain",
  71: "Slight snow",
  73: "Snow",
  75: "Heavy snow",
  77: "Snow grains",
  80: "Slight rain showers",
  81: "Rain showers",
  82: "Heavy rain showers",
  85: "Slight snow showers",
  86: "Heavy snow showers",
  95: "Thunderstorm",
  96: "Thunderstorm + hail",
  99: "Thunderstorm + heavy hail",
};

function weatherLabel(code: number): string {
  return WEATHER_LABELS[code] ?? "Unknown";
}
```

---

## Temperature conversion

Open-Meteo returns Celsius by default. Convert to Fahrenheit when needed:

```ts
function celsiusToFahrenheit(c: number): number {
  return Math.round((c * 9) / 5 + 32);
}
```

Alternatively, request Fahrenheit directly via `&temperature_unit=fahrenheit` in the query string.

---

## TypeScript interfaces

```ts
export interface WeatherCurrent {
  description: string;
  tempF: number;
  humidity: number;
  windSpeedKmh: number;
  windSpeedMph: number;
}

export interface WeatherHour {
  time: string;
  tempF: number;
}

export interface WeatherData {
  current: WeatherCurrent;
  hourly: WeatherHour[];
  timezone: string;
}
```

---

## The useWeather hook

Create at `hooks/useWeather.ts`:

```ts
import { useState, useEffect } from "react";

const DEFAULT_LAT = 37.7749;
const DEFAULT_LNG = -122.4194;

async function fetchWeather(lat: number, lng: number): Promise<WeatherData> {
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.searchParams.set("latitude", String(lat));
  url.searchParams.set("longitude", String(lng));
  url.searchParams.set("current", "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m");
  url.searchParams.set("hourly", "temperature_2m");
  url.searchParams.set("timezone", "auto");
  url.searchParams.set("forecast_days", "1");

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Weather API error: ${res.status}`);
  const data = await res.json();

  const cur = data.current ?? {};
  const tempC = cur.temperature_2m ?? 0;
  const humidity = cur.relative_humidity_2m ?? 0;
  const windKmh = cur.wind_speed_10m ?? 0;
  const windMph = Math.round(windKmh * 0.621371 * 10) / 10;
  const code = cur.weather_code ?? 0;

  const hourly: WeatherHour[] = [];
  const times: string[] = data.hourly?.time ?? [];
  const temps: (number | null)[] = data.hourly?.temperature_2m ?? [];
  const now = new Date();

  for (let i = 0; i < times.length; i++) {
    const t = times[i];
    const temp = temps[i];
    if (t && temp != null) {
      const d = new Date(t);
      if (d >= now) {
        hourly.push({
          time: d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }),
          tempF: celsiusToFahrenheit(temp),
        });
      }
    }
    if (hourly.length >= 6) break;
  }

  return {
    current: {
      description: weatherLabel(code),
      tempF: celsiusToFahrenheit(tempC),
      humidity,
      windSpeedKmh: windKmh,
      windSpeedMph: windMph,
    },
    hourly,
    timezone: data.timezone ?? "auto",
  };
}

export function useWeather(lat?: number | null, lng?: number | null) {
  const latitude = lat ?? DEFAULT_LAT;
  const longitude = lng ?? DEFAULT_LNG;

  const [data, setData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchWeather(latitude, longitude)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load weather");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [latitude, longitude]);

  return { data, loading, error };
}
```

### Hook design patterns

| Pattern | Why |
|---------|-----|
| Cancellation flag (`cancelled`) | Prevents state updates on unmounted components |
| Default coordinates | Widget works immediately without user location |
| Dependency array `[latitude, longitude]` | Re-fetches only when location changes |
| Separate `loading` and `error` states | Enables distinct UI for each state |

---

## Open-Meteo API parameters reference

### Current weather variables

| Variable | Description |
|----------|-------------|
| `temperature_2m` | Air temperature at 2m height (°C) |
| `relative_humidity_2m` | Relative humidity (%) |
| `weather_code` | WMO weather code |
| `wind_speed_10m` | Wind speed at 10m height (km/h) |
| `apparent_temperature` | Feels-like temperature (°C) |
| `precipitation` | Precipitation sum (mm) |

### Hourly variables

| Variable | Description |
|----------|-------------|
| `temperature_2m` | Temperature each hour |
| `precipitation_probability` | Chance of rain (%) |
| `weather_code` | Condition each hour |

### Daily variables

| Variable | Description |
|----------|-------------|
| `temperature_2m_max` | Daily high |
| `temperature_2m_min` | Daily low |
| `weather_code` | Dominant condition |
| `sunrise` | Sunrise time (ISO) |
| `sunset` | Sunset time (ISO) |

### Useful query parameters

| Param | Example | Purpose |
|-------|---------|---------|
| `timezone` | `auto` or `America/Los_Angeles` | Localizes times |
| `forecast_days` | `1`–`16` | Number of days |
| `temperature_unit` | `fahrenheit` | Direct °F responses |
| `wind_speed_unit` | `mph` | Direct mph responses |

---

## CSP considerations

If CSP is enforced, add Open-Meteo to `connect-src`:

```
connect-src 'self' https://api.open-meteo.com;
```
