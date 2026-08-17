/**
 * Maintenance-worker search result types.
 *
 * Search itself is now driven by feature-react-search (see `lib/searchConfig.ts`),
 * which builds and runs its GraphQL at runtime — there is no generated
 * `SearchMaintenanceWorkersQuery` operation type to derive from. This module
 * declares the node shape that the result card and detail modal read, mirroring
 * the Salesforce UI API field-wrapper shape (`{ value, displayValue }`).
 */

/** A Salesforce UI API scalar field wrapper. */
type Field<T> = { value?: T | null; displayValue?: string | null } | null;

export interface MaintenanceWorkerSearchNode {
	Id: string;
	Name?: Field<string>;
	Employment_Type__c?: Field<string>;
	Type__c?: Field<string>;
	Phone__c?: Field<string>;
	Location__c?: Field<string>;
	Rating__c?: Field<number>;
	Hourly_Rate__c?: Field<number>;
	IsActive__c?: Field<boolean>;
}
