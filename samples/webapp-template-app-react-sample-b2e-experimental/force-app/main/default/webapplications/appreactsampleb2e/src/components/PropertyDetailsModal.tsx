import React from "react";
import { X } from "lucide-react";
import { Button } from "./ui/button";
import type { Property } from "../lib/types";

interface PropertyDetailsModalProps {
	property: Property;
	isOpen: boolean;
	onClose: () => void;
}

export const PropertyDetailsModal: React.FC<PropertyDetailsModalProps> = ({
	property,
	isOpen,
	onClose,
}) => {
	if (!isOpen) return null;

	const formatCurrency = (amount: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			minimumFractionDigits: 0,
		}).format(amount);
	};

	const getStatusColor = (status: string) => {
		switch (status.toLowerCase()) {
			case "available":
				return "bg-green-100 text-green-700";
			case "rented":
				return "bg-blue-100 text-blue-700";
			case "maintenance":
				return "bg-yellow-100 text-yellow-700";
			default:
				return "bg-gray-100 text-gray-700";
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center">
			{/* Backdrop */}
			<div className="fixed inset-0 bg-black/50" onClick={onClose} />

			{/* Modal */}
			<div className="relative bg-white rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
				{/* Header */}
				<div className="flex items-center justify-between p-6 border-b border-gray-200">
					<h2 className="text-xl font-semibold text-gray-900">Property Details</h2>
					<button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
						<X className="w-6 h-6" />
					</button>
				</div>

				{/* Content */}
				<div className="p-6 space-y-6">
					{/* Hero Image */}
					{property.heroImage && (
						<div className="w-full h-80 rounded-lg bg-gray-200 overflow-hidden">
							<img
								src={property.heroImage}
								alt={property.name}
								className="w-full h-full object-cover"
							/>
						</div>
					)}

					{/* Property Name and Address */}
					<div>
						<h3 className="text-2xl font-bold text-gray-900">{property.name}</h3>
						<p className="text-base text-gray-600 mt-1">{property.address}</p>
					</div>

					{/* Type, Status, and Rent */}
					<div className="grid grid-cols-3 gap-4">
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Type
							</h4>
							<p className="text-base text-gray-900 capitalize">{property.type}</p>
						</div>
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Status
							</h4>
							<span
								className={`inline-flex px-3 py-1 rounded-full text-sm font-medium capitalize ${getStatusColor(property.status)}`}
							>
								{property.status}
							</span>
						</div>
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Monthly Rent
							</h4>
							<p className="text-xl font-bold text-purple-700">
								{formatCurrency(property.monthlyRent)}
							</p>
						</div>
					</div>

					{/* Property Specifications */}
					<div>
						<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
							Property Specifications
						</h4>
						<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
							{property.bedrooms !== undefined && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Bedrooms</p>
									<p className="text-lg font-semibold text-gray-900">{property.bedrooms}</p>
								</div>
							)}
							{property.bathrooms !== undefined && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Bathrooms</p>
									<p className="text-lg font-semibold text-gray-900">{property.bathrooms}</p>
								</div>
							)}
							{property.sqFt !== undefined && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Square Feet</p>
									<p className="text-lg font-semibold text-gray-900">
										{property.sqFt.toLocaleString()}
									</p>
								</div>
							)}
							{property.yearBuilt !== undefined && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Year Built</p>
									<p className="text-lg font-semibold text-gray-900">{property.yearBuilt}</p>
								</div>
							)}
						</div>
					</div>

					{/* Lease Information */}
					<div>
						<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
							Lease Information
						</h4>
						<div className="grid grid-cols-2 md:grid-cols-3 gap-4">
							{property.deposit !== undefined && (
								<div>
									<p className="text-sm text-gray-600">Security Deposit</p>
									<p className="text-base font-semibold text-gray-900">
										{formatCurrency(property.deposit)}
									</p>
								</div>
							)}
							{property.leaseTerm !== undefined && (
								<div>
									<p className="text-sm text-gray-600">Lease Term</p>
									<p className="text-base font-semibold text-gray-900">
										{property.leaseTerm} months
									</p>
								</div>
							)}
							{property.availableDate && (
								<div>
									<p className="text-sm text-gray-600">Available Date</p>
									<p className="text-base font-semibold text-gray-900">{property.availableDate}</p>
								</div>
							)}
						</div>
					</div>

					{/* Amenities */}
					<div>
						<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
							Amenities
						</h4>
						<div className="flex flex-wrap gap-4">
							{property.parking !== undefined && (
								<div className="flex items-center gap-2">
									<span className="text-lg">🚗</span>
									<span className="text-sm text-gray-700">{property.parking} Parking Space(s)</span>
								</div>
							)}
							{property.petFriendly !== undefined && (
								<div className="flex items-center gap-2">
									<span className="text-lg">{property.petFriendly ? "🐾" : "🚫"}</span>
									<span className="text-sm text-gray-700">
										{property.petFriendly ? "Pet Friendly" : "No Pets"}
									</span>
								</div>
							)}
						</div>
					</div>

					{/* Features */}
					{property.features && property.features.length > 0 && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
								Features
							</h4>
							<div className="flex flex-wrap gap-2">
								{property.features.map((feature, index) => (
									<span
										key={index}
										className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium"
									>
										{feature}
									</span>
								))}
							</div>
						</div>
					)}

					{/* Utilities */}
					{property.utilities && property.utilities.length > 0 && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
								Utilities Included
							</h4>
							<div className="flex flex-wrap gap-2">
								{property.utilities.map((utility, index) => (
									<span
										key={index}
										className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium"
									>
										{utility}
									</span>
								))}
							</div>
						</div>
					)}

					{/* Description */}
					{property.description && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Description
							</h4>
							<p className="text-sm text-gray-700 whitespace-pre-wrap">{property.description}</p>
						</div>
					)}

					{/* Virtual Tour */}
					{property.tourUrl && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Virtual Tour
							</h4>
							<a
								href={property.tourUrl}
								target="_blank"
								rel="noopener noreferrer"
								className="inline-flex items-center gap-2 text-purple-600 hover:text-purple-700 font-medium"
							>
								<span>View Virtual Tour</span>
								<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										strokeWidth={2}
										d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
									/>
								</svg>
							</a>
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200">
					<Button variant="outline" onClick={onClose}>
						Close
					</Button>
				</div>
			</div>
		</div>
	);
};
