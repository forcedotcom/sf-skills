/**
 * Property search result types.
 *
 * Search itself is now driven by feature-react-search (see `lib/searchConfig.ts`),
 * which builds and runs its GraphQL at runtime — there is no generated
 * `SearchPropertiesQuery` operation type to derive from. This module declares the
 * node shape that the property result card and detail modal read, mirroring the
 * Salesforce UI API field-wrapper shape (`{ value, displayValue }`).
 */

/** A Salesforce UI API scalar field wrapper. */
type Field<T> = { value?: T | null; displayValue?: string | null } | null;

export interface PropertySearchNode {
	Id: string;
	Name?: Field<string>;
	Address__c?: Field<string>;
	Description__c?: Field<string>;
	Type__c?: Field<string>;
	Status__c?: Field<string>;
	Hero_Image__c?: Field<string>;
	Tour_URL__c?: Field<string>;
	Features__c?: Field<string>;
	Utilities__c?: Field<string>;
	Available_Date__c?: Field<string>;
	CreatedDate?: Field<string>;
	Monthly_Rent__c?: Field<number>;
	Bedrooms__c?: Field<number>;
	Bathrooms__c?: Field<number>;
	Sq_Ft__c?: Field<number>;
	Year_Built__c?: Field<number>;
	Deposit__c?: Field<number>;
	Lease_Term__c?: Field<number>;
	Parking__c?: Field<number>;
	Pet_Friendly__c?: Field<boolean>;
}
