import { useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWeather, WEATHER_LABELS, type WeatherData, type WeatherHour } from "@/hooks/useWeather";
import {
	Sun,
	Cloud,
	CloudSun,
	CloudRain,
	CloudSnow,
	CloudLightning,
	CloudFog,
	CloudDrizzle,
	Wind,
	Droplets,
	type LucideIcon,
} from "lucide-react";

type ForecastTab = "today" | "tomorrow" | "next3days";

const FORECAST_TABS: { key: ForecastTab; label: string }[] = [
	{ key: "today", label: "Today" },
	{ key: "tomorrow", label: "Tomorrow" },
	{ key: "next3days", label: "Next 3 Days" },
];

/** Tab/panel ids wiring the forecast tablist to its single panel. */
const FORECAST_PANEL_ID = "weather-forecast-panel";
const tabId = (key: ForecastTab) => `weather-tab-${key}`;

const HOURLY_KEY: Record<
	ForecastTab,
	keyof Pick<WeatherData, "todayHourly" | "tomorrowHourly" | "next3DaysHourly">
> = {
	today: "todayHourly",
	tomorrow: "tomorrowHourly",
	next3days: "next3DaysHourly",
};

function getWeatherIcon(code: number, className = "h-16 w-16 text-gray-400") {
	const props = { className, "aria-hidden": true as const };
	if (code <= 1) return <Sun {...props} />;
	if (code === 2) return <CloudSun {...props} />;
	if (code === 3) return <Cloud {...props} />;
	if (code === 45 || code === 48) return <CloudFog {...props} />;
	if (code >= 51 && code <= 55) return <CloudDrizzle {...props} />;
	if (code >= 61 && code <= 65) return <CloudRain {...props} />;
	if (code >= 71 && code <= 77) return <CloudSnow {...props} />;
	if (code >= 80 && code <= 82) return <CloudRain {...props} />;
	if (code >= 85 && code <= 86) return <CloudSnow {...props} />;
	if (code >= 95) return <CloudLightning {...props} />;
	return <Sun {...props} />;
}

const Divider = () => <div className="my-5 border-t border-gray-200" />;

function WeatherSkeleton() {
	return (
		<div className="mt-5" aria-hidden="true">
			{/* CurrentConditions: date row + city */}
			<div className="flex items-baseline justify-between">
				<Skeleton className="h-5 w-32" />
				<Skeleton className="h-5 w-24" />
			</div>

			{/* CurrentConditions: description + temperature + icon */}
			<div className="mt-2 flex items-center justify-between">
				<div>
					<Skeleton className="h-5 w-24" />
					<Skeleton className="mt-1 h-[72px] w-36" />
				</div>
				<Skeleton className="h-20 w-20 rounded-full" />
			</div>

			{/* Divider */}
			<div className="my-5 border-t border-gray-200" />

			{/* CurrentConditions: stats grid */}
			<div className="grid grid-cols-3 gap-2 text-center">
				{[0, 1, 2].map((i) => (
					<div key={i} className="flex flex-col items-center gap-1">
						<Skeleton className="h-5 w-5 rounded-full" />
						<Skeleton className="h-5 w-16" />
						<Skeleton className="h-4 w-12" />
					</div>
				))}
			</div>

			{/* Divider */}
			<div className="my-5 border-t border-gray-200" />

			{/* ForecastTabs */}
			<div className="flex gap-6">
				<Skeleton className="h-5 w-12" />
				<Skeleton className="h-5 w-16" />
				<Skeleton className="h-5 w-20" />
			</div>

			{/* HourlyForecast */}
			<div className="mt-4 flex gap-3 overflow-x-auto pb-1">
				{[0, 1, 2, 3].map((i) => (
					<div
						key={i}
						className="flex min-w-[70px] flex-col items-center gap-1.5 rounded-2xl border border-gray-100 bg-gray-50/80 px-3 py-3"
					>
						<Skeleton className="h-4 w-10" />
						<Skeleton className="h-5 w-5 rounded-full" />
						<Skeleton className="h-5 w-8" />
					</div>
				))}
			</div>
		</div>
	);
}

function StatItem({
	icon: Icon,
	value,
	label,
}: {
	icon: LucideIcon;
	value: string;
	label: string;
}) {
	return (
		<div className="flex flex-col items-center gap-1">
			<Icon className="h-5 w-5 text-gray-400" aria-hidden />
			<p className="text-base font-semibold text-primary">{value}</p>
			<p className="text-xs text-muted-foreground">{label}</p>
		</div>
	);
}

function CurrentConditions({ weather }: { weather: WeatherData }) {
	const { current, city, timezone } = weather;
	return (
		<>
			<div className="flex items-baseline justify-between">
				<p className="text-sm text-muted-foreground">
					{new Date().toLocaleDateString(navigator.language, {
						day: "numeric",
						month: "long",
						year: "numeric",
						timeZone: timezone,
					})}
				</p>
				{city && <p className="text-sm font-medium text-muted-foreground">{city}</p>}
			</div>

			<div className="mt-2 flex items-center justify-between">
				<div>
					<p className="text-base text-foreground">{current.description}</p>
					<p className="text-6xl font-bold tracking-tight text-foreground">
						{current.temp}
						<span className="align-top text-3xl">{current.tempUnit}</span>
					</p>
				</div>
				{getWeatherIcon(current.weatherCode, "h-20 w-20 text-gray-400")}
			</div>

			<Divider />

			<div className="grid grid-cols-3 gap-2 text-center">
				<StatItem icon={Wind} value={`${current.windSpeed} ${current.windUnit}`} label="Wind" />
				<StatItem icon={Droplets} value={`${current.humidity}%`} label="Humidity" />
				<StatItem icon={CloudRain} value={`${current.precipitationProbability}%`} label="Rain" />
			</div>
		</>
	);
}

function ForecastTabs({
	activeTab,
	onTabChange,
}: {
	activeTab: ForecastTab;
	onTabChange: (tab: ForecastTab) => void;
}) {
	// Roving tabindex means only the active tab is in the page tab order, so the
	// ARIA tablist pattern requires arrow/Home/End keys to move selection *and*
	// focus between tabs — otherwise the other tabs become keyboard-unreachable.
	const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

	const onKeyDown = (event: React.KeyboardEvent, index: number) => {
		const last = FORECAST_TABS.length - 1;
		let next: number;
		switch (event.key) {
			case "ArrowRight":
			case "ArrowDown":
				next = index === last ? 0 : index + 1;
				break;
			case "ArrowLeft":
			case "ArrowUp":
				next = index === 0 ? last : index - 1;
				break;
			case "Home":
				next = 0;
				break;
			case "End":
				next = last;
				break;
			default:
				return;
		}
		event.preventDefault();
		onTabChange(FORECAST_TABS[next].key);
		tabRefs.current[next]?.focus();
	};

	return (
		<div className="flex gap-6" role="tablist" aria-label="Forecast range">
			{FORECAST_TABS.map(({ key, label }, index) => {
				const selected = activeTab === key;
				return (
					<button
						key={key}
						type="button"
						role="tab"
						id={tabId(key)}
						ref={(el) => {
							tabRefs.current[index] = el;
						}}
						aria-selected={selected}
						aria-controls={FORECAST_PANEL_ID}
						tabIndex={selected ? 0 : -1}
						onClick={() => onTabChange(key)}
						onKeyDown={(event) => onKeyDown(event, index)}
						className="flex flex-col items-center"
					>
						<span
							className={`text-sm font-semibold ${selected ? "text-foreground" : "text-muted-foreground"}`}
						>
							{label}
						</span>
						{selected && <span className="mt-1 h-1.5 w-1.5 rounded-full bg-foreground" />}
					</button>
				);
			})}
		</div>
	);
}

function HourlyForecast({ hours, activeTab }: { hours: WeatherHour[]; activeTab: ForecastTab }) {
	return (
		<div
			id={FORECAST_PANEL_ID}
			role="tabpanel"
			aria-labelledby={tabId(activeTab)}
			tabIndex={0}
			className="mt-4 flex gap-3 overflow-x-auto pb-1"
		>
			{hours.map((h) => (
				<div
					key={h.time}
					className="flex min-w-[70px] flex-col items-center gap-1.5 rounded-2xl border border-gray-100 bg-gray-50/80 px-3 py-3"
				>
					<p className="whitespace-nowrap text-xs text-muted-foreground">{h.time}</p>
					{getWeatherIcon(h.weatherCode, "h-5 w-5 text-gray-500")}
					<span className="sr-only">{WEATHER_LABELS[h.weatherCode] ?? "Unknown"}</span>
					<p className="text-base font-semibold text-foreground">{h.temp}°</p>
				</div>
			))}
		</div>
	);
}

export function WeatherWidget() {
	const { data: weather, loading, error } = useWeather();
	const [activeTab, setActiveTab] = useState<ForecastTab>("today");

	return (
		<Card className="rounded-2xl border-0 p-6 shadow-md">
			<h2 className="text-lg font-semibold text-primary">Weather</h2>

			{loading && (
				<>
					<span role="status" className="sr-only">
						Loading weather
					</span>
					<WeatherSkeleton />
				</>
			)}

			{error && (
				<p className="mt-4 text-sm text-destructive" role="alert">
					{error}
				</p>
			)}

			{!loading && !error && weather && (
				<div className="mt-5">
					<CurrentConditions weather={weather} />
					<Divider />
					<ForecastTabs activeTab={activeTab} onTabChange={setActiveTab} />
					<HourlyForecast hours={weather[HOURLY_KEY[activeTab]]} activeTab={activeTab} />
				</div>
			)}
		</Card>
	);
}
