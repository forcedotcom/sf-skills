/**
 * Thin GraphQL client: createDataSDK + data.graphql with centralized error handling.
 * Use with gql-tagged queries and generated operation types for type-safe calls.
 */
import { createDataSDK } from '@salesforce/sdk-data';

export async function executeGraphQL<TData, TVariables>(
  query: string,
  variables?: TVariables
): Promise<TData> {
  const data = await createDataSDK();
  // SDK types graphql() first param as string; at runtime it may accept gql DocumentNode too
  const response = await data.graphql?.<TData, TVariables>(query, variables);

  if (!response) {
    throw new Error('GraphQL response is undefined');
  }

  if (response?.errors?.length) {
    const msg = response.errors.map(e => e.message).join('; ');
    throw new Error(`GraphQL Error: ${msg}`);
  }

  return response.data;
}
