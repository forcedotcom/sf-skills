import React from "react";
import { Card } from "../ui/card";
import { Skeleton } from "../ui/skeleton";
import upgraphIcon from "../../assets/icons/upgraph.svg";
import downgraphIcon from "../../assets/icons/downgraph.svg";
import { MoreVertical } from "lucide-react";

interface StatCardProps {
	title: string;
	value?: number | string;
	trend?: {
		value: number;
		isPositive: boolean;
	};
	subtitle?: string;
	loading?: boolean;
	onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
	title,
	value,
	trend,
	subtitle,
	loading,
	onClick,
}) => {
	return (
		<Card
			className={`p-4 border-gray-200 shadow-sm relative ${onClick ? "cursor-pointer hover:shadow-lg transition-shadow" : ""}`}
			onClick={onClick}
		>
			{/* Three-dot menu */}
			<button className="absolute top-4 right-4 p-1 hover:bg-gray-100 rounded-md transition-colors">
				<MoreVertical className="w-4 h-4 text-gray-400" />
			</button>

			<div className="space-y-1">
				<p className="text-sm font-medium text-gray-600 uppercase tracking-wide">{title}</p>
				{loading ? (
					<>
						<div className="flex items-baseline gap-3">
							<Skeleton className="h-9 w-11" />
							<Skeleton className="h-6 w-14 rounded-full" />
						</div>
						<Skeleton className="h-5 w-30 mt-2" />
					</>
				) : (
					<>
						<div className="flex items-baseline gap-3">
							<p className="text-4xl font-bold text-primary-purple">{value}</p>
							{trend && (
								<span
									className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-medium ${
										trend.isPositive ? "bg-cyan-100 text-cyan-800" : "bg-pink-100 text-pink-800"
									}`}
								>
									<img
										src={trend.isPositive ? upgraphIcon : downgraphIcon}
										alt={trend.isPositive ? "Up" : "Down"}
										className="w-4 h-4"
									/>
									{Math.abs(trend.value)}%
								</span>
							)}
						</div>
						{subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
					</>
				)}
			</div>
		</Card>
	);
};
