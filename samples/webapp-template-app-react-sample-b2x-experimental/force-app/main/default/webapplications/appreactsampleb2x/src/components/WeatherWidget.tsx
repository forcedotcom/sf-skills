import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useWeather, type WeatherData, type WeatherHour } from "@/hooks/useWeather";
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
		<div className="mt-5 space-y-5" aria-hidden="true">
			<Skeleton className="h-4 w-32" />
			<div className="flex items-center justify-between">
				<div className="space-y-2">
					<Skeleton className="h-4 w-20" />
					<Skeleton className="h-14 w-32" />
				</div>
				<Skeleton className="h-20 w-20 rounded-full" />
			</div>
			<div className="border-t border-gray-200" />
			<div className="grid grid-cols-3 gap-2">
				{[0, 1, 2].map((i) => (
					<div key={i} className="flex flex-col items-center gap-1.5">
						<Skeleton className="h-5 w-5 rounded-full" />
						<Skeleton className="h-4 w-14" />
						<Skeleton className="h-3 w-10" />
					</div>
				))}
			</div>
			<div className="border-t border-gray-200" />
			<div className="flex gap-6">
				<Skeleton className="h-4 w-12" />
				<Skeleton className="h-4 w-16" />
				<Skeleton className="h-4 w-20" />
			</div>
			<div className="flex gap-3">
				{[0, 1, 2, 3].map((i) => (
					<div
						key={i}
						className="flex w-[70px] flex-col items-center gap-1.5 rounded-2xl border border-gray-100 px-3 py-3"
					>
						<Skeleton className="h-3 w-10" />
						<Skeleton className="h-5 w-5 rounded-full" />
						<Skeleton className="h-4 w-8" />
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
			<Icon className="h-5 w-5 text-gray-400" />
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
	return (
		<div className="flex gap-6">
			{FORECAST_TABS.map(({ key, label }) => (
				<button key={key} onClick={() => onTabChange(key)} className="flex flex-col items-center">
					<span
						className={`text-sm font-semibold ${activeTab === key ? "text-foreground" : "text-muted-foreground"}`}
					>
						{label}
					</span>
					{activeTab === key && <span className="mt-1 h-1.5 w-1.5 rounded-full bg-foreground" />}
				</button>
			))}
		</div>
	);
}

function HourlyForecast({ hours }: { hours: WeatherHour[] }) {
	if (hours.length === 0) return null;
	return (
		<div className="mt-4 flex gap-3 overflow-x-auto pb-1">
			{hours.map((h) => (
				<div
					key={h.time}
					className="flex min-w-[70px] flex-col items-center gap-1.5 rounded-2xl border border-gray-100 bg-gray-50/80 px-3 py-3"
				>
					<p className="whitespace-nowrap text-xs text-muted-foreground">{h.time}</p>
					{getWeatherIcon(h.weatherCode, "h-5 w-5 text-gray-500")}
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

			{loading && <WeatherSkeleton />}

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
					<HourlyForecast hours={weather[HOURLY_KEY[activeTab]]} />
				</div>
			)}
		</Card>
	);
}
