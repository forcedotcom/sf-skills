import React from "react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogFooter,
} from "../ui/dialog";
import type { PropertySearchNode } from "../../api/properties/propertySearchService";

interface PropertyDetailsModalProps {
	property: PropertySearchNode;
	isOpen: boolean;
	onClose: () => void;
}

export const PropertyDetailsModal: React.FC<PropertyDetailsModalProps> = ({
	property,
	isOpen,
	onClose,
}) => {
	const name = property.Name?.value || "Unnamed Property";
	const address = property.Address__c?.value || "Address not available";
	const heroImage = property.Hero_Image__c?.value;
	const description = property.Description__c?.value;
	const propertyType = property.Type__c?.value?.toLowerCase() || "apartment";
	const status = property.Status__c?.value?.toLowerCase() || "available";
	const monthlyRent = property.Monthly_Rent__c?.value || 0;
	const bedrooms = property.Bedrooms__c?.value;
	const bathrooms = property.Bathrooms__c?.value;
	const sqFt = property.Sq_Ft__c?.value;
	const yearBuilt = property.Year_Built__c?.value;
	const deposit = property.Deposit__c?.value;
	const leaseTerm = property.Lease_Term__c?.value;
	const availableDate = property.Available_Date__c?.value;
	const parking = property.Parking__c?.value;
	const petFriendly = property.Pet_Friendly__c?.value;
	const tourUrl = property.Tour_URL__c?.value;
	const features = property.Features__c?.value ? property.Features__c.value.split(";") : undefined;
	const utilities = property.Utilities__c?.value
		? property.Utilities__c.value.split(";")
		: undefined;

	const formatCurrency = (amount: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			minimumFractionDigits: 0,
		}).format(amount);
	};

	const getStatusColor = (s: string) => {
		switch (s) {
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
		<Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
			<DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle>Property Details</DialogTitle>
				</DialogHeader>

				<div className="space-y-6">
					{heroImage && (
						<div className="w-full h-80 rounded-lg bg-gray-200 overflow-hidden">
							<img src={heroImage} alt={name} className="w-full h-full object-cover" />
						</div>
					)}

					<div>
						<h3 className="text-2xl font-bold text-gray-900">{name}</h3>
						<p className="text-base text-gray-600 mt-1">{address}</p>
					</div>

					<div className="grid grid-cols-3 gap-4">
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Type
							</h4>
							<p className="text-base text-gray-900 capitalize">{propertyType}</p>
						</div>
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Status
							</h4>
							<span
								className={`inline-flex px-3 py-1 rounded-full text-sm font-medium capitalize ${getStatusColor(status)}`}
							>
								{status}
							</span>
						</div>
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Monthly Rent
							</h4>
							<p className="text-xl font-bold text-purple-700">{formatCurrency(monthlyRent)}</p>
						</div>
					</div>

					<div>
						<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
							Property Specifications
						</h4>
						<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
							{bedrooms != null && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Bedrooms</p>
									<p className="text-lg font-semibold text-gray-900">{bedrooms}</p>
								</div>
							)}
							{bathrooms != null && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Bathrooms</p>
									<p className="text-lg font-semibold text-gray-900">{bathrooms}</p>
								</div>
							)}
							{sqFt != null && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Square Feet</p>
									<p className="text-lg font-semibold text-gray-900">{sqFt.toLocaleString()}</p>
								</div>
							)}
							{yearBuilt != null && (
								<div className="bg-gray-50 rounded-lg p-4">
									<p className="text-sm text-gray-600">Year Built</p>
									<p className="text-lg font-semibold text-gray-900">{yearBuilt}</p>
								</div>
							)}
						</div>
					</div>

					<div>
						<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
							Lease Information
						</h4>
						<div className="grid grid-cols-2 md:grid-cols-3 gap-4">
							{deposit != null && (
								<div>
									<p className="text-sm text-gray-600">Security Deposit</p>
									<p className="text-base font-semibold text-gray-900">{formatCurrency(deposit)}</p>
								</div>
							)}
							{leaseTerm != null && (
								<div>
									<p className="text-sm text-gray-600">Lease Term</p>
									<p className="text-base font-semibold text-gray-900">{leaseTerm} months</p>
								</div>
							)}
							{availableDate && (
								<div>
									<p className="text-sm text-gray-600">Available Date</p>
									<p className="text-base font-semibold text-gray-900">{availableDate}</p>
								</div>
							)}
						</div>
					</div>

					<div>
						<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
							Amenities
						</h4>
						<div className="flex flex-wrap gap-4">
							{parking != null && (
								<div className="flex items-center gap-2">
									<span className="text-lg">🚗</span>
									<span className="text-sm text-gray-700">{parking} Parking Space(s)</span>
								</div>
							)}
							{petFriendly != null && (
								<div className="flex items-center gap-2">
									<span className="text-lg">{petFriendly ? "🐾" : "🚫"}</span>
									<span className="text-sm text-gray-700">
										{petFriendly ? "Pet Friendly" : "No Pets"}
									</span>
								</div>
							)}
						</div>
					</div>

					{features && features.length > 0 && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
								Features
							</h4>
							<div className="flex flex-wrap gap-2">
								{features.map((feature, index) => (
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

					{utilities && utilities.length > 0 && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
								Utilities Included
							</h4>
							<div className="flex flex-wrap gap-2">
								{utilities.map((utility, index) => (
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

					{description && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Description
							</h4>
							<p className="text-sm text-gray-700 whitespace-pre-wrap">{description}</p>
						</div>
					)}

					{tourUrl && (
						<div>
							<h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
								Virtual Tour
							</h4>
							<a
								href={tourUrl}
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

				<DialogFooter showCloseButton />
			</DialogContent>
		</Dialog>
	);
};
