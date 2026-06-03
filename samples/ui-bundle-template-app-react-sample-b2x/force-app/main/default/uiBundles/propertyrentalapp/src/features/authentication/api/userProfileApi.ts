/**
 * Extensible user profile fetching and updating via UI API GraphQL.
 */
import { createDataSDK } from "@salesforce/platform-sdk";
import { flattenGraphQLRecord } from "../utils/helpers";

const USER_PROFILE_FIELDS_FULL = `
    Id
    FirstName @optional { value }
    LastName @optional { value }
    Email @optional { value }
    Phone @optional { value }
    Street @optional { value }
    City @optional { value }
    State @optional { value }
    PostalCode @optional { value }
    Country @optional { value }`;

const USER_CONTACT_FIELDS = `
    Id
    ContactId @optional { value }`;

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

function throwOnGraphQLErrors(errors: { message: string }[] | undefined): void {
	if (errors?.length) {
		console.error("GraphQL request failed", errors);
		throw new Error("An unexpected error occurred");
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
	const result = await data.graphql!.query<any>({
		query: getUserProfileQuery(fields),
		variables: {
			userId,
		},
	});
	throwOnGraphQLErrors(result.errors);
	return flattenGraphQLRecord<T>(result.data?.uiapi?.query?.User?.edges?.[0]?.node);
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
	const result = await data.graphql!.mutate<any>({
		mutation: getUserProfileMutation(USER_PROFILE_FIELDS_FULL),
		variables: {
			input: { Id: userId, User: { ...values } },
		},
	});
	throwOnGraphQLErrors(result.errors);
	return flattenGraphQLRecord<T>(result.data?.uiapi?.UserUpdate?.Record);
}
