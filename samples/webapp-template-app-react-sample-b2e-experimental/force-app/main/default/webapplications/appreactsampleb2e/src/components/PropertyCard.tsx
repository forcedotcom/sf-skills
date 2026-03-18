import React from "react";
import type { Property } from "../lib/types";

interface PropertyCardProps {
	property: Property;
	onClick?: (property: Property) => void;
}

export const PropertyCard: React.FC<PropertyCardProps> = ({ property, onClick }) => {
	const handleClick = () => {
		if (onClick) {
			onClick(property);
		}
	};

	// Truncate description to approximately 3 lines (around 150 characters)
	const truncatedDescription = property.description
		? property.description.length > 150
			? property.description.substring(0, 150) + "..."
			: property.description
		: "No description available.";

	return (
		<div
			className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
			onClick={handleClick}
		>
			{/* Hero Image */}
			<div className="relative h-48 bg-gray-200">
				{property.heroImage ? (
					<img
						src={property.heroImage}
						alt={property.name}
						className="w-full h-full object-cover"
					/>
				) : (
					<div className="w-full h-full flex items-center justify-center text-gray-400">
						<span className="text-4xl">🏠</span>
					</div>
				)}
			</div>

			{/* Card Content */}
			<div className="p-6">
				{/* Property Name */}
				<h3 className="text-xl font-bold text-gray-900 mb-2">{property.name}</h3>

				{/* Address */}
				<p className="text-sm text-gray-600 mb-4">{property.address}</p>

				{/* Description */}
				<p className="text-sm text-gray-700 mb-4 line-clamp-3">{truncatedDescription}</p>

				{/* Since Year */}
				{property.createdDate && (
					<p className="text-sm text-gray-500 font-medium">Since {property.createdDate}</p>
				)}
			</div>
		</div>
	);
};
