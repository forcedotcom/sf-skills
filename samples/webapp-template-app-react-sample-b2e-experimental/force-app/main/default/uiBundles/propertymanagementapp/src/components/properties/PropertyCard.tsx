import React, { useState } from "react";
import { Home } from "lucide-react";
import type { PropertySearchNode } from "../../api/properties/propertySearchService";

interface PropertyCardProps {
	property: PropertySearchNode;
	onClick?: (property: PropertySearchNode) => void;
}

export const PropertyCard: React.FC<PropertyCardProps> = ({ property, onClick }) => {
	const [imageError, setImageError] = useState(false);

	const handleClick = () => {
		if (onClick) {
			onClick(property);
		}
	};

	const name = property.Name?.value || "Unnamed Property";
	const address = property.Address__c?.value || "Address not available";
	const heroImage = property.Hero_Image__c?.value;
	const description = property.Description__c?.value;
	const createdYear = property.CreatedDate?.value
		? new Date(property.CreatedDate.value).getFullYear().toString()
		: undefined;

	const truncatedDescription = description
		? description.length > 150
			? description.substring(0, 150) + "..."
			: description
		: "No description available.";

	return (
		<div
			className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
			onClick={handleClick}
		>
			<div className="relative h-48 bg-gray-200">
				{heroImage && !imageError ? (
					<img
						src={heroImage}
						alt={name}
						className="w-full h-full object-cover"
						onError={() => setImageError(true)}
					/>
				) : (
					<div className="w-full h-full flex items-center justify-center text-gray-400">
						<Home size={64} strokeWidth={1.5} />
					</div>
				)}
			</div>

			<div className="p-6">
				<h3 className="text-xl font-bold text-gray-900 mb-2">{name}</h3>
				<p className="text-sm text-gray-600 mb-4">{address}</p>
				<p className="text-sm text-gray-700 mb-4 line-clamp-3">{truncatedDescription}</p>
				{createdYear && <p className="text-sm text-gray-500 font-medium">Since {createdYear}</p>}
			</div>
		</div>
	);
};
