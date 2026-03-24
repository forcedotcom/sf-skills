import { Link } from "react-router";
import {
	Breadcrumb,
	BreadcrumbList,
	BreadcrumbItem,
	BreadcrumbLink,
	BreadcrumbSeparator,
	BreadcrumbPage,
} from "../../../components/ui/breadcrumb";
import { Skeleton } from "../../../components/ui/skeleton";

interface ObjectBreadcrumbProps {
	listPath: string;
	listLabel: string;
	recordName?: string;
	loading?: boolean;
	includeHome?: boolean; // default is true
	homeLabel?: string; // default is "Home"
}

export function ObjectBreadcrumb({
	listPath,
	listLabel,
	recordName,
	loading,
	includeHome = true,
	homeLabel = "Home",
}: ObjectBreadcrumbProps) {
	const isDetailView = loading || recordName;

	return (
		<Breadcrumb className="mb-3">
			<BreadcrumbList>
				{includeHome && (
					<BreadcrumbItem>
						<BreadcrumbLink asChild>
							<Link to="/">{homeLabel}</Link>
						</BreadcrumbLink>
					</BreadcrumbItem>
				)}
				<BreadcrumbSeparator />
				{isDetailView ? (
					<>
						<BreadcrumbItem>
							<BreadcrumbLink asChild>
								<Link to={listPath}>{listLabel}</Link>
							</BreadcrumbLink>
						</BreadcrumbItem>
						<BreadcrumbSeparator />
						<BreadcrumbItem>
							{loading && !recordName ? (
								<Skeleton className="h-4 w-32" />
							) : (
								<BreadcrumbPage>{recordName}</BreadcrumbPage>
							)}
						</BreadcrumbItem>
					</>
				) : (
					<BreadcrumbItem>
						<BreadcrumbPage>{listLabel}</BreadcrumbPage>
					</BreadcrumbItem>
				)}
			</BreadcrumbList>
		</Breadcrumb>
	);
}
