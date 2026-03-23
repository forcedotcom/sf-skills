import { useState, useEffect, useRef } from "react";
import { objectDetailService } from "../api/objectDetailService";
import type { LayoutResponse } from "../types/recordDetail/recordDetail";
import type { ObjectInfoResult } from "../types/objectInfo/objectInfo";
import type { GraphQLRecordNode } from "../api/recordListGraphQLService";

export interface UseRecordDetailLayoutReturn {
	layout: LayoutResponse | null;
	record: GraphQLRecordNode | null;
	objectMetadata: ObjectInfoResult | null;
	loading: boolean;
	error: string | null;
}

export interface UseRecordDetailLayoutParams {
	objectApiName: string | null;
	recordId: string | null;
	recordTypeId?: string | null;
	initialData?: {
		layout: LayoutResponse;
		record: GraphQLRecordNode;
		objectMetadata: ObjectInfoResult;
	} | null;
}

const MAX_CACHE_SIZE = 50;
const CACHE_TTL_MS = 5 * 60 * 1000;

type CacheEntry = {
	layout: LayoutResponse;
	record: GraphQLRecordNode;
	objectMetadata: ObjectInfoResult;
	cachedAt: number;
};

export function useRecordDetailLayout({
	objectApiName,
	recordId,
	recordTypeId = null,
	initialData = null,
}: UseRecordDetailLayoutParams): UseRecordDetailLayoutReturn {
	const [layout, setLayout] = useState<LayoutResponse | null>(initialData?.layout ?? null);
	const [record, setRecord] = useState<GraphQLRecordNode | null>(initialData?.record ?? null);
	const [objectMetadata, setObjectMetadata] = useState<ObjectInfoResult | null>(
		initialData?.objectMetadata ?? null,
	);
	const [loading, setLoading] = useState(!initialData);
	const [error, setError] = useState<string | null>(null);

	const cacheKey =
		objectApiName && recordId ? `${objectApiName}:${recordId}:${recordTypeId ?? "default"}` : null;
	const cacheRef = useRef<Map<string, CacheEntry>>(new Map());

	useEffect(() => {
		if (!objectApiName || !recordId) {
			setError("Invalid object or record ID");
			setLoading(false);
			return;
		}

		if (
			initialData?.layout != null &&
			initialData?.record != null &&
			initialData?.objectMetadata != null
		) {
			return;
		}

		const cached = cacheRef.current.get(cacheKey!);
		const now = Date.now();
		if (cached && now - cached.cachedAt < CACHE_TTL_MS) {
			setLayout(cached.layout);
			setRecord(cached.record);
			setObjectMetadata(cached.objectMetadata);
			setLoading(false);
			setError(null);
			return;
		}

		let isCancelled = false;

		const fetchDetail = async () => {
			setLoading(true);
			setError(null);

			try {
				const {
					layout: layoutData,
					record: recordData,
					objectMetadata: objectMetadataData,
				} = await objectDetailService.getRecordDetail(
					objectApiName,
					recordId,
					recordTypeId ?? undefined,
				);

				if (isCancelled) return;

				const cache = cacheRef.current;
				if (cache.size >= MAX_CACHE_SIZE) {
					const firstKey = cache.keys().next().value;
					if (firstKey != null) cache.delete(firstKey);
				}
				cache.set(cacheKey!, {
					layout: layoutData,
					record: recordData,
					objectMetadata: objectMetadataData,
					cachedAt: Date.now(),
				});
				setLayout(layoutData);
				setRecord(recordData);
				setObjectMetadata(objectMetadataData);
			} catch {
				if (isCancelled) return;
				setError("Failed to load record details");
			} finally {
				if (!isCancelled) {
					setLoading(false);
				}
			}
		};

		fetchDetail();

		return () => {
			isCancelled = true;
		};
	}, [objectApiName, recordId, recordTypeId, cacheKey, initialData]);

	return {
		layout,
		record,
		objectMetadata,
		loading,
		error,
	};
}
