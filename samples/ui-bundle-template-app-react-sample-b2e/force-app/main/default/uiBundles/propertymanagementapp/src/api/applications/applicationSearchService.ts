/**
 * Application search result types.
 *
 * Search itself is now driven by feature-react-search (see `lib/searchConfig.ts`),
 * which builds and runs its GraphQL at runtime — there is no generated
 * `SearchApplicationsQuery` operation type to derive from. This module declares the
 * node shape that the result card and detail modal read, mirroring the Salesforce
 * UI API field-wrapper shape (`{ value, displayValue }`).
 */

/** A Salesforce UI API scalar field wrapper. */
type Field<T> = { value?: T | null; displayValue?: string | null } | null;

export interface ApplicationSearchNode {
	Id: string;
	Name?: Field<string>;
	Status__c?: Field<string>;
	Start_Date__c?: Field<string>;
	Employment__c?: Field<string>;
	References__c?: Field<string>;
	User__r?: {
		Name?: Field<string>;
	} | null;
	Property__r?: {
		Name?: Field<string>;
		Address__c?: Field<string>;
	} | null;
}
