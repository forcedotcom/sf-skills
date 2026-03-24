import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { IssuesDonutChart } from "../components/IssuesDonutChart";
import { MaintenanceTable } from "../components/MaintenanceTable";
import { GlobalSearchBar } from "../features/object-search/components/GlobalSearchBar";
import { StatCard } from "../components/StatCard";
import { PageContainer } from "../components/layout/PageContainer";
import { PageLoadingState } from "../components/feedback/PageLoadingState";
import { getDashboardMetrics, calculateMetrics } from "../api/dashboard";
import type { DashboardMetrics, MaintenanceRequest } from "../lib/types";
import {
	PROPERTY_OBJECT_API_NAME,
	SEARCHABLE_OBJECTS,
	type SearchableObjectConfig,
} from "../features/object-search/config/searchableObjects";
import { nodeToMaintenanceRequest } from "../lib/maintenanceAdapter";
import { PATHS } from "../lib/routeConfig";

const CHART_ISSUE_TYPES = ["Plumbing", "HVAC", "Electrical", "Appliance", "Pest"] as const;
const CHART_COLORS = ["#7C3AED", "#EC4899", "#14B8A6", "#06B6D4", "#F59E0B"] as const;

export default function Home() {
	const navigate = useNavigate();

	const [searchQuery, setSearchQuery] = useState("");
	const [selectedObjectApiName, setSelectedObjectApiName] =
		useState<SearchableObjectConfig["objectApiName"]>(PROPERTY_OBJECT_API_NAME);

	const selectedConfig = useMemo(
		() => SEARCHABLE_OBJECTS.find((o) => o.objectApiName === selectedObjectApiName),
		[selectedObjectApiName],
	);
	const labelPlural = selectedConfig?.fallbackLabelPlural ?? "Records";

	const [metrics, setMetrics] = useState<DashboardMetrics>({
		totalProperties: 0,
		unitsAvailable: 0,
		occupiedUnits: 0,
		topMaintenanceIssue: "",
		topMaintenanceIssueCount: 0,
	});
	const [metricsLoading, setMetricsLoading] = useState(true);
	const [maintenanceRequests, setMaintenanceRequests] = useState<MaintenanceRequest[]>([]);

	useEffect(() => {
		let cancelled = false;
		(async () => {
			try {
				setMetricsLoading(true);
				const { properties, maintenanceRequests: rawRequests } = await getDashboardMetrics();
				if (!cancelled) {
					setMetrics(calculateMetrics(properties));
					setMaintenanceRequests(
						(rawRequests as Record<string, unknown>[]).map((node) =>
							nodeToMaintenanceRequest(node),
						),
					);
				}
			} catch (error) {
				if (!cancelled) console.error("Error loading dashboard metrics:", error);
			} finally {
				if (!cancelled) setMetricsLoading(false);
			}
		})();
		return () => {
			cancelled = true;
		};
	}, []);

	const handleSearchSubmit = useCallback(() => {
		const trimmed = searchQuery.trim();
		const path = selectedConfig?.path ?? SEARCHABLE_OBJECTS[0].path;
		if (trimmed) {
			navigate(`${path}?q=${encodeURIComponent(trimmed)}`);
		} else {
			navigate(path);
		}
	}, [searchQuery, navigate, selectedConfig?.path]);

	const handleBrowseAll = useCallback(() => {
		navigate(selectedConfig?.path ?? SEARCHABLE_OBJECTS[0].path);
	}, [navigate, selectedConfig?.path]);

	const handleViewMaintenance = useCallback(() => {
		navigate(PATHS.MAINTENANCE_REQUESTS);
	}, [navigate]);

	const chartData = useMemo(() => {
		const counts: Record<string, number> = {
			Plumbing: 0,
			HVAC: 0,
			Electrical: 0,
			Appliance: 0,
			Pest: 0,
		};
		maintenanceRequests.forEach((request) => {
			const type = request.issueType;
			if (CHART_ISSUE_TYPES.includes(type as (typeof CHART_ISSUE_TYPES)[number])) {
				counts[type]++;
			}
		});
		return [
			{ name: "Plumbing", value: counts.Plumbing, color: CHART_COLORS[0] },
			{ name: "HVAC", value: counts.HVAC, color: CHART_COLORS[1] },
			{ name: "Electrical", value: counts.Electrical, color: CHART_COLORS[2] },
			{ name: "Appliance", value: counts.Appliance, color: CHART_COLORS[3] },
			{ name: "Pest Control", value: counts.Pest, color: CHART_COLORS[4] },
		];
	}, [maintenanceRequests]);

	const trends = useMemo(() => {
		const totalPropertiesTrend = Math.round(metrics.totalProperties * 0.1);
		const unitsAvailableTrend = Math.round(metrics.unitsAvailable * 0.1);
		const occupiedUnitsTrend = Math.round(metrics.occupiedUnits * 0.1);
		return {
			totalProperties: {
				trend: totalPropertiesTrend,
				previous: metrics.totalProperties - totalPropertiesTrend,
			},
			unitsAvailable: {
				trend: unitsAvailableTrend,
				previous: metrics.unitsAvailable + unitsAvailableTrend,
			},
			occupiedUnits: {
				trend: occupiedUnitsTrend,
				previous: metrics.occupiedUnits - occupiedUnitsTrend,
			},
		};
	}, [metrics]);

	if (metricsLoading) {
		return <PageLoadingState message="Loading dashboard..." />;
	}

	return (
		<PageContainer>
			<div className="max-w-7xl mx-auto space-y-6">
				<GlobalSearchBar
					searchableObjects={SEARCHABLE_OBJECTS}
					selectedObjectApiName={selectedObjectApiName}
					onSelectedObjectChange={setSelectedObjectApiName}
					searchQuery={searchQuery}
					onSearchQueryChange={setSearchQuery}
					onSearchSubmit={handleSearchSubmit}
					onBrowseAll={handleBrowseAll}
					labelPlural={labelPlural}
				/>

				<div className="grid grid-cols-1 lg:grid-cols-[70%_30%] gap-6">
					<div className="space-y-6">
						<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
							<StatCard
								title="Total Properties"
								value={metrics.totalProperties}
								trend={{ value: trends.totalProperties.trend, isPositive: true }}
								subtitle={`Last month total ${trends.totalProperties.previous}`}
							/>
							<StatCard
								title="Units Available"
								value={metrics.unitsAvailable}
								trend={{ value: trends.unitsAvailable.trend, isPositive: false }}
								subtitle={`Last month total ${trends.unitsAvailable.previous}/${metrics.totalProperties}`}
							/>
							<StatCard
								title="Occupied Units"
								value={metrics.occupiedUnits}
								trend={{ value: trends.occupiedUnits.trend, isPositive: true }}
								subtitle={`Last month total ${trends.occupiedUnits.previous}`}
							/>
						</div>
						<MaintenanceTable requests={maintenanceRequests} onView={handleViewMaintenance} />
					</div>
					<div>
						<IssuesDonutChart data={chartData} />
					</div>
				</div>
			</div>
		</PageContainer>
	);
}
