/**
 * Real weather data via Open-Meteo (free, no API key).
 * Detects user location via Geolocation API; falls back to San Francisco.
 */
import { useState, useEffect } from "react";
import { useCachedAsyncData } from "@/features/object-search/hooks/useCachedAsyncData";

const FALLBACK = {
	LAT: 37.7749,
	LNG: -122.4194,
	CITY: "San Francisco",
	TIMEZONE: "America/Los_Angeles",
} as const;
const IMPERIAL_REGIONS = new Set(["US", "LR", "MM"]);
const MIN_TODAY_TILES = 3;

/** WMO weather codes → short label (Open-Meteo) */
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

/** Splits an API timestamp like "2026-03-12T21:00" into its date and hour parts. */
function parseTimestamp(ts: string): { dateStr: string; hour: number } {
	const [date, time] = ts.split("T");
	return { dateStr: date!, hour: Number(time?.split(":")[0]) };
}

/** Returns { date: "YYYY-MM-DD", hour: 0-23 } for a Date in the given IANA timezone. */
function datePartsInTimezone(
	date: Date,
	timezone: string,
	locale: string,
): { date: string; hour: number } {
	const fmt = new Intl.DateTimeFormat(locale, {
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "numeric",
		hour12: false,
		timeZone: timezone,
	});
	const p = Object.fromEntries(fmt.formatToParts(date).map((x) => [x.type, x.value]));
	return { date: `${p.year}-${p.month}-${p.day}`, hour: Number(p.hour) };
}

/** Formats an hour (0-23) as a localized time string like "9 PM" or "21". */
function formatHourLabel(hour: number, locale: string): string {
	// Dummy date — only the hour matters. Avoids parsing API timestamps through
	// new Date(ts), which would misinterpret them in the user's local timezone.
	return new Date(2000, 0, 1, hour).toLocaleTimeString(locale, { hour: "numeric" });
}

/** Returns the short weekday name for a "YYYY-MM-DD" date string. */
function weekdayLabel(dateStr: string, locale: string): string {
	// Parse at noon UTC and format in UTC so the user's local timezone can't shift the date.
	return new Date(dateStr + "T12:00:00Z").toLocaleDateString(locale, {
		weekday: "short",
		timeZone: "UTC",
	});
}

function isImperialLocale(): boolean {
	const region = navigator.language.split("-")[1]?.toUpperCase() ?? "";
	return IMPERIAL_REGIONS.has(region);
}

async function reverseGeocode(lat: number, lng: number): Promise<string> {
	try {
		const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=10`;
		const response = await fetch(url, {
			headers: { "Accept-Language": navigator.language },
		});
		if (!response.ok) return "";
		const data = (await response.json()) as {
			address?: { city?: string; town?: string; village?: string; county?: string };
		};
		const addr = data.address;
		return addr?.city ?? addr?.town ?? addr?.village ?? addr?.county ?? "";
	} catch {
		return "";
	}
}

export type TempUnit = "°F" | "°C";
export type WindUnit = "mph" | "km/h";

export interface WeatherCurrent {
	description: string;
	temp: number;
	tempUnit: TempUnit;
	humidity: number;
	windSpeed: number;
	windUnit: WindUnit;
	weatherCode: number;
	precipitationProbability: number;
}

export interface WeatherHour {
	time: string;
	temp: number;
	weatherCode: number;
}

export interface WeatherData {
	current: WeatherCurrent;
	city: string;
	todayHourly: WeatherHour[];
	tomorrowHourly: WeatherHour[];
	next3DaysHourly: WeatherHour[];
	timezone: string;
}

interface OpenMeteoResponse {
	current?: {
		temperature_2m?: number;
		relative_humidity_2m?: number;
		weather_code?: number;
		wind_speed_10m?: number;
	};
	hourly?: {
		time?: string[];
		temperature_2m?: (number | null)[];
		weather_code?: (number | null)[];
		precipitation_probability?: (number | null)[];
	};
	timezone?: string;
}

async function fetchWeather(lat: number, lng: number): Promise<WeatherData> {
	const url = new URL("https://api.open-meteo.com/v1/forecast");
	url.searchParams.set("latitude", String(lat));
	url.searchParams.set("longitude", String(lng));
	url.searchParams.set(
		"current",
		"temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
	);
	url.searchParams.set("hourly", "temperature_2m,weather_code,precipitation_probability");
	url.searchParams.set("timezone", "auto");
	url.searchParams.set("forecast_days", "4");

	const [response, geocodedCity] = await Promise.all([
		fetch(url.toString()),
		reverseGeocode(lat, lng),
	]);
	if (!response.ok) throw new Error(`Weather failed: ${response.status}`);

	const data = (await response.json()) as OpenMeteoResponse;
	const timezone = data.timezone ?? FALLBACK.TIMEZONE;
	const locale = navigator.language;
	const imperial = isImperialLocale();
	const tempUnit: TempUnit = imperial ? "°F" : "°C";
	const windUnit: WindUnit = imperial ? "mph" : "km/h";
	const convertTemp = (c: number) => (imperial ? Math.round((c * 9) / 5 + 32) : Math.round(c));
	const convertWind = (kmh: number) =>
		imperial ? Math.round(kmh * 0.621371 * 10) / 10 : Math.round(kmh * 10) / 10;

	const cur = data.current ?? {};
	const { date: todayDateStr, hour: currentHour } = datePartsInTimezone(
		new Date(),
		timezone,
		locale,
	);
	const [y, m, d] = todayDateStr.split("-").map(Number);
	const tomorrowDateStr = new Date(Date.UTC(y!, m! - 1, d! + 1)).toISOString().slice(0, 10);

	const {
		time: times = [],
		temperature_2m: temps = [],
		weather_code: codes = [],
		precipitation_probability: precips = [],
	} = data.hourly ?? {};

	let precipProbability = 0;
	let foundPrecip = false;
	const todayFuture: WeatherHour[] = [];
	const tomorrowAll: WeatherHour[] = [];
	const tomorrowHourly: WeatherHour[] = [];
	const next3DaysHourly: WeatherHour[] = [];

	for (let i = 0; i < times.length; i++) {
		const ts = times[i];
		if (!ts) continue;

		const { dateStr, hour: entryHour } = parseTimestamp(ts);
		const isFuture =
			dateStr > todayDateStr || (dateStr === todayDateStr && entryHour >= currentHour);

		if (!foundPrecip && isFuture) {
			precipProbability = precips[i] ?? 0;
			foundPrecip = true;
		}

		const tempC = temps[i];
		if (tempC == null) continue;

		const timeLabel = formatHourLabel(entryHour, locale);
		const entry: WeatherHour = {
			time: timeLabel,
			temp: convertTemp(tempC),
			weatherCode: codes[i] ?? 0,
		};

		if (dateStr === todayDateStr && isFuture) {
			todayFuture.push(entry);
		}
		if (dateStr === tomorrowDateStr) {
			tomorrowAll.push(entry);
			if (entryHour % 3 === 0) {
				tomorrowHourly.push(entry);
			}
		}
		if (dateStr > todayDateStr && entryHour % 6 === 0) {
			next3DaysHourly.push({
				...entry,
				time: weekdayLabel(dateStr, locale) + " " + timeLabel,
			});
		}
	}

	const backfill = Math.max(0, MIN_TODAY_TILES - todayFuture.length);
	const todayHourly = [...todayFuture, ...tomorrowAll.slice(0, backfill)];

	return {
		current: {
			description: WEATHER_LABELS[cur.weather_code ?? 0] ?? "Unknown",
			temp: convertTemp(cur.temperature_2m ?? 0),
			tempUnit,
			humidity: cur.relative_humidity_2m ?? 0,
			windSpeed: convertWind(cur.wind_speed_10m ?? 0),
			windUnit,
			weatherCode: cur.weather_code ?? 0,
			precipitationProbability: precipProbability,
		},
		city: geocodedCity || FALLBACK.CITY,
		todayHourly,
		tomorrowHourly,
		next3DaysHourly,
		timezone,
	};
}

interface GeoPosition {
	latitude: number;
	longitude: number;
	resolved: boolean;
}

function useGeolocation(): GeoPosition {
	const [position, setPosition] = useState<GeoPosition>(() => ({
		latitude: FALLBACK.LAT,
		longitude: FALLBACK.LNG,
		resolved: typeof navigator === "undefined" || !navigator.geolocation,
	}));

	useEffect(() => {
		if (!navigator.geolocation) return;
		navigator.geolocation.getCurrentPosition(
			(pos) =>
				setPosition({
					latitude: pos.coords.latitude,
					longitude: pos.coords.longitude,
					resolved: true,
				}),
			() => setPosition((prev) => ({ ...prev, resolved: true })),
		);
	}, []);

	return position;
}

export function useWeather(lat?: number | null, lng?: number | null) {
	const geo = useGeolocation();
	const latitude = lat ?? geo.latitude;
	const longitude = lng ?? geo.longitude;
	const canFetch = lat != null || geo.resolved;

	const cached = useCachedAsyncData(
		() => fetchWeather(latitude, longitude),
		[latitude, longitude, canFetch],
		{ key: `weather:${latitude},${longitude}:${canFetch}`, ttl: 300_000 },
	);

	if (!canFetch) {
		return { data: null, loading: true, error: null };
	}

	return { data: cached.data, loading: cached.loading, error: cached.error };
}
