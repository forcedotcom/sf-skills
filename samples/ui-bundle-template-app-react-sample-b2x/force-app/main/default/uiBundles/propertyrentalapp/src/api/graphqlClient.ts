/**
 * Thin GraphQL client: createDataSDK + sdk.graphql.query with centralized
 * error handling. Use with gql-tagged queries and generated operation types
 * for type-safe calls.
 */
import { createDataSDK } from '@salesforce/platform-sdk';

export async function executeGraphQL<TData, TVariables>(
  query: string,
  variables?: TVariables
): Promise<TData> {
  const data = await createDataSDK();
  const result = await data.graphql!.query<TData, TVariables>({
    query: query,
    variables: variables,
  });

  if (result.errors?.length) {
    const msg = result.errors.map(e => e.message).join('; ');
    throw new Error(`GraphQL Error: ${msg}`);
  }

  if (result.data == null) {
    throw new Error('GraphQL response data is null');
  }

  return result.data;
}
