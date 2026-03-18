import type { PicklistValue as GraphQLPicklistValue } from "../objectInfo/objectInfo";

export type PicklistValue = GraphQLPicklistValue & {
	value: NonNullable<GraphQLPicklistValue["value"]>;
	label: NonNullable<GraphQLPicklistValue["label"]>;
};
