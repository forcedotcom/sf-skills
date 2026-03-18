import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card } from "./ui/card";
import { MoreVertical } from "lucide-react";

interface ChartData {
	name: string;
	value: number;
	color: string;
}

interface IssuesDonutChartProps {
	data: ChartData[];
}

export const IssuesDonutChart: React.FC<IssuesDonutChartProps> = ({ data }) => {
	const total = data.reduce((sum, item) => sum + item.value, 0);
	const maxValue = data.length > 0 ? Math.max(...data.map((item) => item.value)) : 0;
	const mainPercentage = total > 0 ? Math.round((maxValue / total) * 100) : 0;

	const CustomTooltip = ({ active, payload }: any) => {
		if (active && payload && payload.length) {
			const percentage = total > 0 ? Math.round((payload[0].value / total) * 100) : 0;
			return (
				<div className="bg-white p-3 border border-gray-200 rounded shadow-lg z-50">
					<p className="text-sm font-semibold text-gray-800">{payload[0].name}</p>
					<p className="text-sm text-gray-600">
						Count: <span className="font-medium">{payload[0].value}</span>
					</p>
					<p className="text-sm text-gray-600">
						Percentage: <span className="font-medium">{percentage}%</span>
					</p>
				</div>
			);
		}
		return null;
	};

	return (
		<Card className="p-4 border-gray-200 shadow-sm flex flex-col relative">
			{/* Three-dot menu */}
			<button className="absolute top-4 right-4 p-1 hover:bg-gray-100 rounded-md transition-colors z-10">
				<MoreVertical className="w-4 h-4 text-gray-400" />
			</button>

			<h3 className="text-sm font-medium text-primary-purple mb-2 uppercase tracking-wide">
				Top Maintenance Issues
			</h3>
			<div className="relative flex items-center justify-center">
				<ResponsiveContainer width="100%" height={300}>
					<PieChart>
						<Pie
							data={data}
							cx="50%"
							cy="50%"
							innerRadius={70}
							outerRadius={110}
							paddingAngle={2}
							dataKey="value"
						>
							{data.map((entry, index) => (
								<Cell key={`cell-${index}`} fill={entry.color} />
							))}
						</Pie>
						<Tooltip content={<CustomTooltip />} wrapperStyle={{ zIndex: 1000 }} />
					</PieChart>
				</ResponsiveContainer>
				{/* Center text */}
				<div className="absolute inset-0 flex items-center justify-center pointer-events-none">
					<div className="text-center">
						<div className="text-5xl font-bold text-primary-purple">{mainPercentage}%</div>
					</div>
				</div>
			</div>
			{/* Legend */}
			<div className="mt-6 grid grid-cols-2 gap-3">
				{data.map((item, index) => (
					<div key={index} className="flex items-center gap-2">
						<div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
						<span className="text-sm text-gray-700">{item.name}</span>
					</div>
				))}
			</div>
		</Card>
	);
};
