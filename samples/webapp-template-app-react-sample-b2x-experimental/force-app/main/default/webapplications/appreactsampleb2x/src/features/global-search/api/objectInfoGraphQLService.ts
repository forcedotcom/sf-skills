/**
 * Object metadata GraphQL service (uiapi.objectInfos).
 *
 * Single endpoint for object describe and picklist values. Used by objectInfoService
 * to implement getObjectInfoBatch and getPicklistValues. Not used directly by UI.
 *
 * @module api/objectInfoGraphQLService
 */

import { createDataSDK, gql } from "@salesforce/sdk-data";
import type {
	GetObjectInfosQuery,
	GetObjectInfosQueryVariables,
	GetPicklistValuesQuery,
	GetPicklistValuesQueryVariables,
	ObjectInfoInput,
} from "../types/schema";

/**
 * Builds objectInfos query (metadata only). Uses apiNames only — do not pass objectInfoInputs.
 */
const OBJECT_INFOS_QUERY = gql`
	query GetObjectInfos($apiNames: [String!]!) {
		uiapi {
			objectInfos(apiNames: $apiNames) {
				ApiName
				label
				labelPlural
				nameFields
				defaultRecordTypeId
				keyPrefix
				layoutable
				queryable
				searchable
				updateable
				deletable
				createable
				custom
				mruEnabled
				feedEnabled
				fields {
					ApiName
					label
					dataType
					relationshipName
					reference
					compound
					compoundFieldName
					compoundComponentName
					controllingFields
					controllerName
					referenceToInfos {
						ApiName
						nameFields
					}
				}
				recordTypeInfos {
					recordTypeId
					name
					master
					available
					defaultRecordTypeMapping
				}
				themeInfo {
					color
					iconUrl
				}
				childRelationships {
					relationshipName
					fieldName
					childObjectApiName
				}
				dependentFields {
					controllingField
				}
			}
		}
	}
`;

/**
 * Builds objectInfos query with picklist values (API v65.0+).
 * Schema requires objectInfos to be called with either apiNames or objectInfoInputs, not both.
 * This query uses objectInfoInputs only.
 * Optimized to only fetch fields used by extractPicklistValuesFromGraphQLObjectInfo.
 */
const PICKLIST_VALUES_QUERY = gql`
	query GetPicklistValues($objectInfoInputs: [ObjectInfoInput!]!) {
		uiapi {
			objectInfos(objectInfoInputs: $objectInfoInputs) {
				ApiName
				fields {
					ApiName
					... on PicklistField {
						picklistValuesByRecordTypeIDs {
							recordTypeID
							defaultValue {
								value
							}
							picklistValues {
								label
								value
								validFor
							}
						}
					}
				}
			}
		}
	}
`;

export async function queryForObjectInfos(apiNames: string[]): Promise<GetObjectInfosQuery> {
	return runQuery<GetObjectInfosQuery, GetObjectInfosQueryVariables>(OBJECT_INFOS_QUERY, {
		apiNames,
	});
}

export async function queryForPicklistValues(
	objectInfoInputs: ObjectInfoInput[],
): Promise<GetPicklistValuesQuery> {
	return runQuery<GetPicklistValuesQuery, GetPicklistValuesQueryVariables>(PICKLIST_VALUES_QUERY, {
		objectInfoInputs,
	});
}

async function runQuery<Q, V>(query: string, variables: V): Promise<Q> {
	const data = await createDataSDK();
	const response = await data.graphql?.<Q, V>(query, variables);

	if (response?.errors?.length) {
		const errorMessages = response.errors.map((e) => e.message).join("; ");
		throw new Error(`GraphQL Error: ${errorMessages}`);
	}

	return response?.data ?? ({} as Q);
}
