import { useEffect, useMemo } from "react";
import type { LayoutResponse } from "../../types/recordDetail/recordDetail";
import { useRecordDetailLayout } from "../../hooks/useRecordDetailLayout";
import { toRecordDisplayNameMetadata } from "../../utils/fieldUtils";
import { DetailForm } from "./DetailForm";
import type { ObjectInfoResult } from "../../types/objectInfo/objectInfo";
import type { ObjectInfoMetadata } from "../../utils/formDataTransformUtils";
import type { ObjectInfo } from "../../utils/layoutTransformUtils";
import type { GraphQLRecordNode } from "../../api/recordListGraphQLService";
import { getGraphQLRecordDisplayName } from "../../utils/graphQLNodeFieldUtils";

export interface UiApiDetailFormProps {
	objectApiName: string;
	recordId: string;
	recordTypeId?: string | null;
	/** When provided, skips fetching and uses this layout (controlled mode). */
	layout?: LayoutResponse | null;
	/** When provided with layout, skips fetching and uses this record (controlled mode). */
	record?: GraphQLRecordNode | null;
	/** When provided, skips fetching and uses this object metadata (controlled mode). */
	objectMetadata?: ObjectInfoResult | null;
	/** When true, shows a loading spinner until layout and record are ready. */
	loadsWithSpinner?: boolean;
	/** Reserved for future edit mode; no-op in read-only. */
	hideFooter?: boolean;
	/** Callback when layout and record are ready (e.g. for parent to show record title). */
	onRecordDataUpdate?: (payload: { recordName: string; record: unknown }) => void;
}

/**
 * Entry component for the record detail view. When layout/record are not provided,
 * fetches them via useRecordDetailLayout. Shows optional loading spinner and renders
 * a read-only DetailForm when ready. Mirrors LWC uiApiDetailForm (read-only).
 *
 * Passes objectInfo (mapped from object metadata) to DetailForm for layout transform.
 * lookupRecords (picklist/lookup options) are not fetched in this flow; DetailForm
 * accepts them when provided (e.g. from a future picklist API). Omit for read-only
 * display without API-driven picklist labels.
 */
export function UiApiDetailForm({
	objectApiName,
	recordId,
	recordTypeId = null,
	layout: layoutProp,
	record: recordProp,
	objectMetadata: objectMetadataProp,
	loadsWithSpinner = false,
	onRecordDataUpdate,
}: UiApiDetailFormProps) {
	// Memoize so hook dependency doesn't change every render (avoids duplicate fetches)
	const initialData = useMemo(
		() =>
			layoutProp && recordProp && objectMetadataProp
				? {
						layout: layoutProp,
						record: recordProp,
						objectMetadata: objectMetadataProp,
					}
				: null,
		[layoutProp, recordProp, objectMetadataProp],
	);

	const fetched = useRecordDetailLayout({
		objectApiName,
		recordId,
		recordTypeId,
		initialData,
	});

	const layout = layoutProp ?? fetched.layout;
	const record = recordProp ?? fetched.record;
	const metadata = objectMetadataProp ?? fetched.objectMetadata;
	const loading = layoutProp == null || recordProp == null ? fetched.loading : false;
	const error = layoutProp == null || recordProp == null ? fetched.error : null;

	const objectInfo: ObjectInfo | null = useMemo(() => {
		if (!metadata?.fields) return null;
		const apiName = metadata.ApiName;
		return {
			apiName,
			fields: Object.fromEntries(
				Object.entries(metadata.fields).map(([name, f]) => [
					name,
					{
						compoundFieldName: f.compoundFieldName ?? undefined,
						dataType: f.dataType ?? "",
					},
				]),
			),
		};
	}, [metadata]);

	const isReadyToRender = Boolean(layout && record && layout.sections?.length);

	const showSpinner = !isReadyToRender && loadsWithSpinner && loading;

	useEffect(() => {
		if (!record || !onRecordDataUpdate || !isReadyToRender) return;
		onRecordDataUpdate({
			recordName: getGraphQLRecordDisplayName(record, toRecordDisplayNameMetadata(metadata)),
			record,
		});
	}, [record, metadata, onRecordDataUpdate, isReadyToRender]);

	if (showSpinner) {
		return (
			<div
				className="min-h-[80px] flex items-center justify-center"
				role="status"
				aria-live="polite"
				aria-label="Loading record details"
			>
				<span className="sr-only">Loading record details</span>
				<div
					className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
					aria-hidden
				/>
			</div>
		);
	}

	if (error || !layout || !record) {
		return null;
	}

	if (!isReadyToRender) {
		return null;
	}

	return (
		<DetailForm
			layout={layout}
			record={record}
			metadata={metadata as ObjectInfoMetadata}
			objectInfo={objectInfo}
			showSectionHeaders
			collapsibleSections
		/>
	);
}
