# Weather UI — Implementation Guide

## Weather card component

Render the weather data inside a Card component:

```tsx
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { useWeather } from "@/hooks/useWeather";

interface WeatherCardProps {
  lat?: number;
  lng?: number;
}

export default function WeatherCard({ lat, lng }: WeatherCardProps) {
  const { data: weather, loading, error } = useWeather(lat, lng);

  return (
    <Card className="rounded-2xl shadow-md">
      <CardHeader>
        <CardTitle className="text-primary">Weather</CardTitle>
        <p className="text-sm text-muted-foreground">
          {new Date().toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {loading && <p className="text-sm text-muted-foreground">Loading weather…</p>}
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        {!loading && !error && weather && (
          <>
            {/* Current conditions */}
            <p className="text-base text-foreground">{weather.current.description}</p>
            <p className="text-4xl font-bold text-foreground">{weather.current.tempF}°F</p>
            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span>{weather.current.windSpeedMph} mph Wind</span>
              <span>{weather.current.humidity}% Humidity</span>
            </div>

            {/* Tab indicator */}
            <div className="flex gap-2 border-b border-border pb-2">
              <span className="border-b-2 border-primary pb-1 text-sm font-semibold text-primary">
                Today
              </span>
            </div>

            {/* Hourly forecast */}
            {weather.hourly.length > 0 && (
              <div className="flex flex-wrap gap-4">
                {weather.hourly.map((h) => (
                  <div key={h.time} className="min-w-[60px] rounded-xl bg-muted/50 p-2 text-center">
                    <p className="text-xs text-muted-foreground">{h.time}</p>
                    <p className="text-base font-semibold text-foreground">{h.tempF}°</p>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## Layout placement

### Dashboard sidebar

Place the weather card in a two-column grid alongside other dashboard content:

```tsx
<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
  <div className="space-y-6">
    {/* Primary dashboard content */}
  </div>
  <div>
    <WeatherCard />
  </div>
</div>
```

### Full-width widget

For a standalone weather section:

```tsx
<section className="mx-auto max-w-md">
  <WeatherCard />
</section>
```

---

## Loading state

Show a text indicator while data is fetching:

```tsx
{loading && <p className="text-sm text-muted-foreground">Loading weather…</p>}
```

For a richer skeleton:

```tsx
{loading && (
  <div className="space-y-3">
    <div className="h-4 w-24 animate-pulse rounded bg-muted" />
    <div className="h-10 w-16 animate-pulse rounded bg-muted" />
    <div className="flex gap-4">
      <div className="h-4 w-20 animate-pulse rounded bg-muted" />
      <div className="h-4 w-20 animate-pulse rounded bg-muted" />
    </div>
  </div>
)}
```

---

## Error state

Show error messages with proper ARIA:

```tsx
{error && (
  <p className="text-sm text-destructive" role="alert">
    {error}
  </p>
)}
```

---

## Extending to daily forecast

To show a multi-day forecast, update the `fetchWeather` function to request daily data:

```ts
url.searchParams.set("daily", "weather_code,temperature_2m_max,temperature_2m_min");
url.searchParams.set("forecast_days", "7");
```

Then render each day:

```tsx
{weather.daily.map((day) => (
  <div key={day.date} className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
    <span className="text-sm text-muted-foreground">{day.dayName}</span>
    <span className="text-sm font-medium">{day.highF}° / {day.lowF}°</span>
    <span className="text-xs text-muted-foreground">{day.description}</span>
  </div>
))}
```

---

## Using browser geolocation

To auto-detect the user's location:

```ts
import { useState, useEffect } from "react";

export function useUserLocation(): { lat: number | null; lng: number | null; error: string | null } {
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLng(pos.coords.longitude);
      },
      (err) => {
        setError(err.message);
      }
    );
  }, []);

  return { lat, lng, error };
}
```

Combine with the weather hook:

```tsx
const { lat, lng } = useUserLocation();
const { data: weather } = useWeather(lat, lng);
```

Falls back to the default location if geolocation is denied or unavailable.

---

## Accessibility

- Error messages use `role="alert"` for screen reader announcement.
- Temperature values include the unit symbol (`°F` or `°C`) in the text.
- Hourly forecast items are visually distinct with background color and spacing.
- Loading state provides text feedback, not just spinners.
