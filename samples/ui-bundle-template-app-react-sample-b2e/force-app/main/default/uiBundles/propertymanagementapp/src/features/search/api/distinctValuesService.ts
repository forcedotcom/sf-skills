/**
 * Fetches distinct values for a picklist field via the uiapi aggregate
 * `groupBy` query.
 *
 * Used by the auto-render pathway when a picklist filter does not declare
 * inline `options`. Each call hits the GraphQL endpoint once and returns the
 * sorted set of distinct values plus their display labels.
 */

import { createDataSDK } from "@salesforce/platform-sdk";

export interface PicklistOption {
	value: string;
	label: string;
}

const KEY_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

function assertValidIdentifier(name: string, kind: string): void {
	if (!KEY_PATTERN.test(name)) {
		throw new Error(
			`Invalid ${kind} "${name}". Must match /^[A-Za-z_][A-Za-z0-9_]*$/ to be a valid GraphQL identifier.`,
		);
	}
}

/**
 * Builds and executes a `uiapi.aggregate.<objectName>(groupBy: { <field>: { group: true } })`
 * query and extracts the distinct values.
 */
export async function fetchDistinctValues(
	objectName: string,
	fieldName: string,
): Promise<PicklistOption[]> {
	assertValidIdentifier(objectName, "objectName");
	assertValidIdentifier(fieldName, "fieldName");

	const document = `query DistinctValues {
		uiapi {
			aggregate {
				${objectName}(groupBy: { ${fieldName}: { group: true } }) {
					edges {
						node {
							aggregate @optional {
								${fieldName} @optional {
									value
									displayValue
									label
								}
							}
						}
					}
				}
			}
		}
	}`;

	const data = await createDataSDK();
	const response = await data.graphql!.query<unknown>({ query: document });

	if (response.errors?.length) {
		throw new Error(response.errors.map((e) => e.message).join("; "));
	}

	const root = response.data as Record<string, unknown> | undefined;
	const aggregate = (root?.uiapi as Record<string, unknown> | undefined)?.aggregate as
		| Record<string, unknown>
		| undefined;
	const objectAgg = aggregate?.[objectName] as
		| { edges?: Array<{ node?: { aggregate?: Record<string, unknown> } }> }
		| undefined;
	const edges = objectAgg?.edges ?? [];

	return edges
		.map((edge) => {
			const field = edge?.node?.aggregate?.[fieldName] as
				| { value?: string | null; displayValue?: string | null; label?: string | null }
				| undefined;
			const value = field?.value;
			if (value == null || value === "") return null;
			return { value, label: field?.label ?? field?.displayValue ?? value };
		})
		.filter((opt): opt is PicklistOption => opt !== null);
}
