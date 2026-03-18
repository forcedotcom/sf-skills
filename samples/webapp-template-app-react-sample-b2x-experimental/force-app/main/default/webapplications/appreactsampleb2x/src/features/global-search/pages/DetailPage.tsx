import { useMemo } from "react";
import { useParams, useNavigate } from "react-router";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Skeleton } from "../../../components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "../../../components/ui/alert";
import { AlertCircle } from "lucide-react";
import DetailHeader from "../components/detail/DetailHeader";
import { UiApiDetailForm } from "../components/detail/UiApiDetailForm";
import { OBJECT_API_NAMES, DEFAULT_DETAIL_PAGE_TITLE } from "../constants";
import { toRecordDisplayNameMetadata } from "../utils/fieldUtils";
import { useRecordDetailLayout } from "../hooks/useRecordDetailLayout";
import { getGraphQLRecordDisplayName } from "../utils/graphQLNodeFieldUtils";

export default function DetailPage() {
	const { objectApiName: objectApiNameParam, recordId } = useParams<{
		objectApiName: string;
		recordId: string;
	}>();
	const navigate = useNavigate();
	const objectApiName = objectApiNameParam ?? OBJECT_API_NAMES[0];

	const { layout, record, objectMetadata, loading, error } = useRecordDetailLayout({
		objectApiName,
		recordId: recordId ?? null,
	});

	const recordTitle = useMemo(
		() =>
			record
				? getGraphQLRecordDisplayName(record, toRecordDisplayNameMetadata(objectMetadata))
				: DEFAULT_DETAIL_PAGE_TITLE,
		[record, objectMetadata],
	);

	const handleBack = () => navigate(-1);

	if (loading) {
		return (
			<div
				className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
				role="status"
				aria-live="polite"
				aria-label="Loading record details"
			>
				<span className="sr-only">Loading record details</span>
				<Skeleton className="h-10 w-32 mb-6" aria-hidden="true" />
				<Card aria-hidden="true">
					<CardHeader>
						<Skeleton className="h-8 w-3/4" />
					</CardHeader>
					<CardContent className="space-y-4">
						{[1, 2, 3, 4].map((i) => (
							<div key={i} className="space-y-2">
								<Skeleton className="h-4 w-24" />
								<Skeleton className="h-4 w-full" />
							</div>
						))}
					</CardContent>
				</Card>
			</div>
		);
	}

	if (error) {
		return (
			<div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
				<DetailHeader title="" onBack={handleBack} />
				<Alert variant="destructive" role="alert">
					<AlertCircle className="h-4 w-4" aria-hidden="true" />
					<AlertTitle>Error</AlertTitle>
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			</div>
		);
	}

	if (!layout || !record) {
		return (
			<div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
				<DetailHeader title="" onBack={handleBack} />
				<Alert role="alert">
					<AlertCircle className="h-4 w-4" aria-hidden="true" />
					<AlertTitle>Not Found</AlertTitle>
					<AlertDescription>Record not found</AlertDescription>
				</Alert>
			</div>
		);
	}

	return (
		<main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12" aria-label="Record details">
			<DetailHeader title={recordTitle} onBack={handleBack} />
			<Card>
				<CardHeader>
					<CardTitle className="text-2xl">{recordTitle}</CardTitle>
				</CardHeader>
				<CardContent>
					<UiApiDetailForm
						objectApiName={objectApiName}
						recordId={recordId!}
						layout={layout}
						record={record}
						objectMetadata={objectMetadata}
					/>
				</CardContent>
			</Card>
		</main>
	);
}
