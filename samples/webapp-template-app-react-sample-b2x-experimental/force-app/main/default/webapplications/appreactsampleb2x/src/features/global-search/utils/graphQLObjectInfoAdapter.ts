/**
 * GraphQL objectInfos → REST-compatible object info and picklist.
 *
 * graphQLObjectInfoToObjectInfoResult / graphQLObjectInfosToBatchResponse: used by objectInfoService
 * after getObjectInfosGraphQL. extractPicklistValuesFromGraphQLObjectInfo: used for getPicklistValues.
 * Normalizes casing and adds synthetic compound fields (e.g. BillingAddress) for layout/dataType.
 *
 * @module utils/graphQLObjectInfoAdapter
 */

import type {
	ObjectInfoBatchResponse,
	GetObjectInfosQueryObjectInfos,
	GetPicklistValuesQueryObjectInfo,
	GetPicklistValuesQueryField,
	GetObjectInfosQueryObjectInfo,
	ObjectInfoResult,
	PicklistValue as GraphQLPicklistValue,
} from "../types/objectInfo/objectInfo";
import type { PicklistValue } from "../types/filters/picklist";

export function graphQLObjectInfoToObjectInfoResult(
	objectInfo: GetObjectInfosQueryObjectInfo,
): ObjectInfoResult {
	const { fields, ...rest } = objectInfo;
	const fieldsRecord = Object.fromEntries((fields ?? []).map((field) => [field?.ApiName, field]));
	return {
		...rest,
		fields: fieldsRecord,
	};
}

/** Convert GraphQL objectInfos array to ObjectInfoBatchResponse (REST shape). */
export function graphQLObjectInfosToBatchResponse(
	objectInfos: GetObjectInfosQueryObjectInfos,
	_requestedApiNames: string[],
): ObjectInfoBatchResponse {
	const results = objectInfos.map((objectInfo) => ({
		result: graphQLObjectInfoToObjectInfoResult(objectInfo!),
		statusCode: 200,
	}));
	return { results };
}

/**
 * Extract picklist values for a field from a GraphQL ObjectInfo node (raw response).
 * Uses picklistValuesByRecordTypeIDs; prefers the given recordTypeId or first available.
 */
export function extractPicklistValuesFromGraphQLObjectInfo(
	objectInfo: NonNullable<GetPicklistValuesQueryObjectInfo>,
	fieldName: string,
	recordTypeId?: string,
): PicklistValue[] {
	const fields = objectInfo.fields;
	if (fields == null) return [];
	const fieldMap: Record<string, GetPicklistValuesQueryField> = Object.fromEntries(
		fields.map((field) => {
			return [field?.ApiName, field];
		}),
	);
	const field = fieldMap[fieldName];
	if (!field) return [];
	const picklistData =
		"picklistValuesByRecordTypeIDs" in field ? field.picklistValuesByRecordTypeIDs : undefined;
	if (!picklistData) return [];
	const rtId = recordTypeId ?? "012000000000000AAA";
	const byRecordType = picklistData.find((p) => p!.recordTypeID === rtId) ?? picklistData[0];
	return mapPicklistValues(byRecordType?.picklistValues ?? []);
}

function mapPicklistValues(values: GraphQLPicklistValue[]): PicklistValue[] {
	return values.map((item) => ({
		...item,
		value: item.value ?? "",
		label: item.label ?? "",
	}));
}
