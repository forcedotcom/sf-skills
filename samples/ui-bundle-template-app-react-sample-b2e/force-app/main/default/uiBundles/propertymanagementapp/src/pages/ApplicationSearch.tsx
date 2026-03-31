import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "../components/ui/sonner";
import {
	searchApplications,
	fetchDistinctApplicationStatus,
} from "../api/applications/applicationSearchService";
import { useCachedAsyncData } from "../features/object-search/hooks/useCachedAsyncData";
import {
	useObjectSearchParams,
	type UseObjectSearchParamsReturn,
} from "../features/object-search/hooks/useObjectSearchParams";
import type { FilterFieldConfig } from "../features/object-search/utils/filterUtils";
import type { SortFieldConfig } from "../features/object-search/utils/sortUtils";
import type { ApplicationSearchNode } from "../api/applications/applicationSearchService";
import { PageHeader } from "../components/layout/PageHeader";
import { PageContainer } from "../components/layout/PageContainer";
import {
	FilterProvider,
	FilterResetButton,
} from "../features/object-search/components/FilterContext";
import { FilterRow } from "../components/layout/FilterRow";
import { SearchFilter } from "../features/object-search/components/filters/SearchFilter";
import { MultiSelectFilter } from "../features/object-search/components/filters/MultiSelectFilter";
import { DateFilter } from "../features/object-search/components/filters/DateFilter";
import { ObjectSearchErrorState } from "../components/shared/ObjectSearchErrorState";
import PaginationControls from "../features/object-search/components/PaginationControls";
import { ApplicationDetailsModal } from "../components/applications/ApplicationDetailsModal";
import { Skeleton } from "../components/ui/skeleton";
import {
	Table,
	TableHeader,
	TableBody,
	TableRow,
	TableHead,
	TableCell,
} from "../components/ui/table";
import { updateApplicationStatus } from "../api/applications/applications";
import type {
	Application__C_Filter,
	Application__C_OrderBy,
} from "../api/graphql-operations-types";
import { ResultOrder } from "../api/graphql-operations-types";
import { Badge } from "../components/ui/badge";
import { PAGINATION_CONFIG } from "../lib/constants";
import { User } from "lucide-react";
import { cn } from "../lib/utils";

const SEARCH_PLACEHOLDER = "Search by application #, applicant, or address...";

const FILTER_CONFIGS: FilterFieldConfig[] = [
	{
		field: "search",
		label: "Search",
		type: "search",
		searchFields: ["Name", "User__r.Name", "Property__r.Address__c"],
		placeholder: SEARCH_PLACEHOLDER,
	},
	{ field: "Status__c", label: "Status", type: "picklist" },
	{ field: "Start_Date__c", label: "Start Date", type: "date" },
	{ field: "CreatedDate", label: "Created Date", type: "datetime" },
];

const SORT_CONFIGS: SortFieldConfig<string>[] = [
	{ field: "Name", label: "Application" },
	{ field: "Status__c", label: "Status" },
	{ field: "Start_Date__c", label: "Start Date" },
	{ field: "CreatedDate", label: "Created Date" },
];

export default function ApplicationSearch() {
	const [selectedApplication, setSelectedApplication] = useState<ApplicationSearchNode | null>(
		null,
	);

	const { data: statusOptions } = useCachedAsyncData(fetchDistinctApplicationStatus, [], {
		key: "distinctApplicationStatus",
		ttl: 30_000,
	});

	const { filters, query, pagination, resetAll } = useObjectSearchParams<
		Application__C_Filter,
		Application__C_OrderBy
	>(FILTER_CONFIGS, SORT_CONFIGS, PAGINATION_CONFIG);
	const effectiveOrderBy = useMemo<Application__C_OrderBy>(
		() => query.orderBy ?? { CreatedDate: { order: ResultOrder.Desc } },
		[query.orderBy],
	);
	const searchKey = `applications:${JSON.stringify({ where: query.where, orderBy: effectiveOrderBy, first: pagination.pageSize, after: pagination.afterCursor })}`;
	const { data, loading, error } = useCachedAsyncData(
		() =>
			searchApplications({
				where: query.where,
				orderBy: effectiveOrderBy,
				first: pagination.pageSize,
				after: pagination.afterCursor,
			}),
		[query.where, effectiveOrderBy, pagination.pageSize, pagination.afterCursor],
		{ key: searchKey },
	);

	const validApplicationNodes = useMemo(
		() =>
			(data?.edges ?? []).reduce<ApplicationSearchNode[]>((acc, edge) => {
				if (edge?.node) acc.push(edge.node);
				return acc;
			}, []),
		[data?.edges],
	);

	const pageInfo = data?.pageInfo;
	const hasNextPage = pageInfo?.hasNextPage ?? false;
	const hasPreviousPage = pagination.pageIndex > 0;

	const handleSaveStatus = async (applicationId: string, status: string) => {
		try {
			const success = await updateApplicationStatus(applicationId, status);
			if (success) {
				if (selectedApplication?.Id === applicationId) {
					setSelectedApplication({ ...selectedApplication, Status__c: { value: status } });
				}
				toast.success("Status updated", {
					description: "Application status has been updated successfully.",
				});
			} else {
				toast.error("Update failed", {
					description: "Failed to update application status. Please try again.",
				});
			}
		} catch (err) {
			console.error(err);
			toast.error("Error updating status", {
				description: "An error occurred while updating the status. Please try again.",
			});
		}
	};

	return (
		<>
			<PageContainer>
				<PageHeader title="Applications" description="Manage and review rental applications" />
				<ApplicationSearchFilters
					filters={filters}
					statusOptions={statusOptions ?? []}
					resetAll={resetAll}
				/>
				<div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
					<Table>
						<ApplicationSearchTableHeader />
						<TableBody>
							{loading && <ApplicationSearchSkeleton pageSize={pagination.pageSize} />}

							{!loading && error && <ApplicationSearchErrorState />}

							{!loading && !error && validApplicationNodes.length === 0 && (
								<ApplicationSearchNoResults />
							)}

							{!loading && !error && validApplicationNodes.length > 0 && (
								<ApplicationSearchTable
									applicationNodes={validApplicationNodes}
									setSelectedApplication={setSelectedApplication}
								/>
							)}
						</TableBody>
					</Table>
				</div>

				<PaginationControls
					pageIndex={pagination.pageIndex}
					hasNextPage={hasNextPage}
					hasPreviousPage={hasPreviousPage}
					pageSize={pagination.pageSize}
					pageSizeOptions={PAGINATION_CONFIG.validPageSizes}
					onNextPage={() => {
						if (pageInfo?.endCursor) pagination.goToNextPage(pageInfo.endCursor);
					}}
					onPreviousPage={pagination.goToPreviousPage}
					onPageSizeChange={pagination.setPageSize}
					disabled={loading || !!error}
				/>
			</PageContainer>

			{!loading && !error && selectedApplication && (
				<ApplicationDetailsModal
					application={selectedApplication}
					isOpen={!!selectedApplication}
					onClose={() => setSelectedApplication(null)}
					onSave={handleSaveStatus}
				/>
			)}
		</>
	);
}

function ApplicationSearchFilters({
	filters,
	statusOptions,
	resetAll,
}: {
	filters: UseObjectSearchParamsReturn<Application__C_Filter, Application__C_OrderBy>["filters"];
	statusOptions: Array<{ value: string; label: string }>;
	resetAll: () => void;
}) {
	return (
		<FilterProvider
			filters={filters.active}
			onFilterChange={filters.set}
			onFilterRemove={filters.remove}
			onReset={resetAll}
		>
			<FilterRow ariaLabel="Applications filters">
				<SearchFilter
					field="search"
					label="Search"
					placeholder={SEARCH_PLACEHOLDER}
					className="w-full sm:w-80"
				/>
				<MultiSelectFilter
					field="Status__c"
					label="Status"
					options={statusOptions ?? []}
					className="w-full sm:w-36"
				/>
				<DateFilter field="Start_Date__c" label="Start Date" className="w-full sm:w-56" />
				<DateFilter
					field="CreatedDate"
					label="Created Date"
					filterType="datetime"
					className="w-full sm:w-56"
				/>
				<FilterResetButton />
			</FilterRow>
		</FilterProvider>
	);
}

function ApplicationSearchTableHeader() {
	return (
		<TableHeader>
			<TableRow>
				<TableHead className="w-1/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Application
				</TableHead>
				<TableHead className="w-5/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Applicant
				</TableHead>
				<TableHead className="w-3/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Start Date
				</TableHead>
				<TableHead className="w-3/12 px-6 py-4 bg-gray-50 text-sm font-semibold text-purple-700 uppercase tracking-wide">
					Status
				</TableHead>
			</TableRow>
		</TableHeader>
	);
}

function ApplicationSearchNoResults() {
	return (
		<TableRow>
			<TableCell colSpan={4} className="text-center py-12 text-gray-500">
				No applications found
			</TableCell>
		</TableRow>
	);
}

function ApplicationSearchTable({
	applicationNodes,
	setSelectedApplication,
}: {
	applicationNodes: ApplicationSearchNode[];
	setSelectedApplication: (application: ApplicationSearchNode) => void;
}) {
	return (
		<>
			{applicationNodes.map((application) => {
				const applicationName = application.Name?.value || "";
				const applicantName = application.User__r?.Name?.value || "Unknown";
				const propertyName = application.Property__r?.Name?.value;
				const propertyAddress = application.Property__r?.Address__c?.value || "";
				const startDate = application.Start_Date__c?.value || application.CreatedDate?.value || "";
				const status = application.Status__c?.value || "Unknown";
				return (
					<TableRow
						key={application.Id}
						onClick={() => setSelectedApplication(application)}
						className="hover:bg-gray-50 transition-colors cursor-pointer"
					>
						<TableCell className="px-6 py-4">
							<div className="text-sm font-medium text-gray-900">{applicationName}</div>
						</TableCell>
						<TableCell className="px-6 py-4">
							<div className="flex items-center">
								<div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center flex-shrink-0">
									<User className="w-5 h-5 text-purple-700" />
								</div>
								<div className="ml-4">
									<div className="text-sm font-medium text-gray-900">{applicantName}</div>
									<div className="text-sm text-gray-500">{propertyName || propertyAddress}</div>
								</div>
							</div>
						</TableCell>
						<TableCell className="px-6 py-4">
							<div className="text-sm text-gray-900">{formatDate(startDate)}</div>
						</TableCell>
						<TableCell className="px-6 py-4">
							<Badge className={cn("text-sm", getStatusColor(status))}>{status}</Badge>
						</TableCell>
					</TableRow>
				);
			})}
		</>
	);
}

const getStatusColor = (status: string) => {
	const statusLower = status.toLowerCase();
	if (statusLower.includes("approved")) return "bg-green-100 text-green-700";
	if (statusLower.includes("rejected")) return "bg-red-100 text-red-700";
	if (statusLower.includes("background")) return "bg-blue-100 text-blue-700";
	if (statusLower.includes("review")) return "bg-yellow-100 text-yellow-700";
	return "bg-gray-100 text-gray-700";
};

const formatDate = (dateString: string) => {
	if (!dateString) return "N/A";
	try {
		const date = new Date(dateString);
		return date.toLocaleDateString("en-US", {
			year: "numeric",
			month: "short",
			day: "numeric",
		});
	} catch {
		return dateString;
	}
};

function ApplicationSearchSkeleton({ pageSize }: { pageSize: number }) {
	return (
		<>
			{Array.from({ length: pageSize }, (_, i) => (
				<TableRow key={i}>
					<TableCell className="px-6 py-4">
						<Skeleton className="h-4 w-24" />
					</TableCell>
					<TableCell className="px-6 py-4">
						<div className="flex items-center">
							<Skeleton className="h-10 w-10 rounded-full shrink-0" />
							<div className="ml-4 space-y-2">
								<Skeleton className="h-4 w-32" />
								<Skeleton className="h-3 w-48" />
							</div>
						</div>
					</TableCell>
					<TableCell className="px-6 py-4">
						<Skeleton className="h-4 w-24" />
					</TableCell>
					<TableCell className="px-6 py-4">
						<Skeleton className="h-6 w-20 rounded-full" />
					</TableCell>
				</TableRow>
			))}
		</>
	);
}

function ApplicationSearchErrorState() {
	const navigate = useNavigate();

	return (
		<TableRow>
			<TableCell colSpan={4} className="p-0">
				<ObjectSearchErrorState
					message="There was an error loading the applications. Please try again."
					onGoHome={() => navigate("/")}
					onRetry={() => navigate(0)}
				/>
			</TableCell>
		</TableRow>
	);
}
