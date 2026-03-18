/**
 * Extensible user profile fetching and updating via UI API GraphQL.
 */
import { createDataSDK } from "@salesforce/sdk-data";
import { flattenGraphQLRecord } from "../utils/helpers";

const USER_PROFILE_FIELDS_FULL = `
    Id
    FirstName { value }
    LastName { value }
    Email { value }
    Phone { value }
    Street { value }
    City { value }
    State { value }
    PostalCode { value }
    Country { value }`;

const USER_CONTACT_FIELDS = `
    Id
    ContactId { value }`;

function getUserProfileQuery(fields: string): string {
	return `
    query GetUserProfile($userId: ID) {
        uiapi {
            query {
                User(where: { Id: { eq: $userId } }) {
                    edges {
                        node {${fields}}
                    }
                }
            }
        }
    }`;
}

function getUserProfileMutation(fields: string): string {
	return `
    mutation UpdateUserProfile($input: UserUpdateInput!) {
      uiapi {
        UserUpdate(input: $input) {
          Record {${fields}}
        }
      }
    }`;
}

function throwOnGraphQLErrors(response: any): void {
	if (response?.errors?.length) {
		throw new Error(response.errors.map((e: any) => e.message).join("; "));
	}
}

/**
 * Fetches the user profile via GraphQL and returns a flattened record.
 * @param userId - The Salesforce User Id.
 * @param fields - GraphQL field selection (defaults to USER_PROFILE_FIELDS_FULL).
 */
export async function fetchUserProfile<T>(
	userId: string,
	fields: string = USER_PROFILE_FIELDS_FULL,
): Promise<T> {
	const data = await createDataSDK();
	const response: any = await data.graphql?.(getUserProfileQuery(fields), {
		userId,
	});
	throwOnGraphQLErrors(response);
	return flattenGraphQLRecord<T>(response?.data?.uiapi?.query?.User?.edges?.[0]?.node);
}

/**
 * Fetches the user's associated contact record ID via GraphQL and returns a flattened record.
 * @param userId - The Salesforce User Id.
 */
export async function fetchUserContact<T>(userId: string): Promise<T> {
	return fetchUserProfile<T>(userId, USER_CONTACT_FIELDS);
}

/**
 * Updates the user profile via GraphQL and returns the flattened updated record.
 * @param userId - The Salesforce User Id.
 * @param values - The field values to update.
 */
export async function updateUserProfile<T>(
	userId: string,
	values: Record<string, unknown>,
): Promise<T> {
	const data = await createDataSDK();
	const response: any = await data.graphql?.(getUserProfileMutation(USER_PROFILE_FIELDS_FULL), {
		input: { Id: userId, User: { ...values } },
	});
	throwOnGraphQLErrors(response);
	return flattenGraphQLRecord<T>(response?.data?.uiapi?.UserUpdate?.Record);
}
