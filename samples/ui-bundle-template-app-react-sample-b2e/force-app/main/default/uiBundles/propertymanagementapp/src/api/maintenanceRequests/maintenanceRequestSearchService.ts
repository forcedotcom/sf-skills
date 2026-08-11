/**
 * Maintenance-request search result types.
 *
 * Search itself is now driven by feature-react-search (see `lib/searchConfig.ts`),
 * which builds and runs its GraphQL at runtime — there is no generated
 * `SearchMaintenanceRequestsQuery` operation type to derive from. This module
 * declares the node shape that the result card and detail modal read, mirroring
 * the Salesforce UI API field-wrapper shape (`{ value, displayValue }`).
 */

/** A Salesforce UI API scalar field wrapper. */
type Field<T> = { value?: T | null; displayValue?: string | null } | null;

export interface MaintenanceRequestSearchNode {
	Id: string;
	Name?: Field<string>;
	Type__c?: Field<string>;
	Priority__c?: Field<string>;
	Status__c?: Field<string>;
	Description__c?: Field<string>;
	Scheduled__c?: Field<string>;
	Property__r?: {
		Name?: Field<string>;
		Address__c?: Field<string>;
	} | null;
	Assigned_Worker__r?: {
		Name?: Field<string>;
	} | null;
	User__r?: {
		Name?: Field<string>;
	} | null;
}
