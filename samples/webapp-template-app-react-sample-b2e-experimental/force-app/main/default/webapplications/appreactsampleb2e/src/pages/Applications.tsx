import { useEffect, useState } from "react";
import { useListPage } from "../hooks/useListPage";
import { applicationsListConfig } from "../lib/listPageConfig";
import { ListPageWithFilters } from "../components/list/ListPageWithFilters";
import { PageHeader } from "../components/layout/PageHeader";
import { ApplicationsTable } from "../components/ApplicationsTable";
import { ApplicationDetailsModal } from "../components/ApplicationDetailsModal";
import { updateApplicationStatus } from "../api/applications";
import type { Application } from "../lib/types";

export default function Applications() {
	const list = useListPage(applicationsListConfig);
	const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);
	const [notification, setNotification] = useState<{
		message: string;
		type: "success" | "error";
	} | null>(null);

	useEffect(() => {
		if (notification) {
			const timer = setTimeout(() => setNotification(null), 5000);
			return () => clearTimeout(timer);
		}
	}, [notification]);

	const handleRowClick = (application: Application) => {
		setSelectedApplication(application);
	};

	const handleCloseModal = () => {
		setSelectedApplication(null);
	};

	const handleSaveStatus = async (applicationId: string, status: string) => {
		try {
			const success = await updateApplicationStatus(applicationId, status);
			if (success) {
				if (selectedApplication?.id === applicationId) {
					setSelectedApplication({ ...selectedApplication, status });
				}
				setNotification({ message: "Application status updated successfully!", type: "success" });
			} else {
				setNotification({ message: "Failed to update application status", type: "error" });
			}
		} catch (error) {
			console.error("Error updating application:", error);
			setNotification({ message: "An error occurred while updating the status", type: "error" });
		}
	};

	return (
		<>
			{notification && (
				<div className="fixed top-4 right-4 z-50 animate-slide-in">
					<div
						className={`px-6 py-4 rounded-lg shadow-lg ${
							notification.type === "success" ? "bg-green-500 text-white" : "bg-red-500 text-white"
						}`}
					>
						<div className="flex items-center gap-3">
							<span className="text-lg">{notification.type === "success" ? "✓" : "✕"}</span>
							<p className="font-medium">{notification.message}</p>
						</div>
					</div>
				</div>
			)}

			<PageHeader title="Applications" description="Manage and review rental applications" />

			<ListPageWithFilters
				filterProps={{
					filters: list.filters,
					picklistValues: list.picklistValues,
					formValues: list.formValues,
					onFormValueChange: list.onFormValueChange,
					onApply: list.onApplyFilters,
					onReset: list.onResetFilters,
					ariaLabel: applicationsListConfig.filtersAriaLabel,
				}}
				filterError={list.filterError}
				loading={list.loading}
				error={list.error}
				loadingMessage={applicationsListConfig.loadingMessage}
				isEmpty={list.items.length === 0}
				searchPlaceholder="Search by applicant, property, status..."
				searchAriaLabel="Search applications"
			>
				<ApplicationsTable applications={list.items} onRowClick={handleRowClick} />

				{list.canLoadMore && (
					<div className="flex justify-center mt-6">
						<button
							type="button"
							onClick={list.onLoadMore}
							disabled={list.loadMoreLoading}
							className="px-6 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-lg text-sm font-medium disabled:opacity-50"
						>
							{list.loadMoreLoading ? "Loading..." : "Load More"}
						</button>
					</div>
				)}
			</ListPageWithFilters>

			{selectedApplication && (
				<ApplicationDetailsModal
					application={selectedApplication}
					isOpen={!!selectedApplication}
					onClose={handleCloseModal}
					onSave={handleSaveStatus}
				/>
			)}
		</>
	);
}
