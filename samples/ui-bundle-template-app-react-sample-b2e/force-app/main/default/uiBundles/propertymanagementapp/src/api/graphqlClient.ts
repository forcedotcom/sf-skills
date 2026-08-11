/**
 * Thin GraphQL client: createDataSDK + sdk.graphql with centralized error
 * handling. Mutations are routed to sdk.graphql.mutate and everything else to
 * sdk.graphql.query (the SDK rejects an operation sent to the wrong method).
 * Use with gql-tagged queries and generated operation types for type-safe calls.
 */
import { createDataSDK } from '@salesforce/platform-sdk';

/**
 * True when the operation's first definition is a `mutation`. Strips GraphQL
 * comments first so a leading `# ...` line can't mask the keyword. Queries
 * (named or anonymous `{ ... }` shorthand) and subscriptions fall through to
 * query().
 */
function isMutation(operation: string): boolean {
  return /^\s*mutation\b/.test(operation.replace(/#[^\n\r]*/g, ''));
}

export async function executeGraphQL<TData, TVariables>(
  operation: string,
  variables?: TVariables
): Promise<TData> {
  const data = await createDataSDK();
  const result = isMutation(operation)
    ? await data.graphql!.mutate<TData, TVariables>({
        mutation: operation,
        variables: variables,
      })
    : await data.graphql!.query<TData, TVariables>({
        query: operation,
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
