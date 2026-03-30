/**
 * Downloads the full GraphQL schema from a connected Salesforce org via introspection.
 *
 * Usage:
 *   npm run graphql:schema
 *   node scripts/get-graphql-schema.mjs [output-path]
 *
 * The default output path matches the schema location expected by codegen.yml
 * and .graphqlrc.yml so that codegen and IDE tooling resolve it automatically.
 */
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { getOrgInfo } from '@salesforce/webapp-experimental/app';
import { buildClientSchema, getIntrospectionQuery, printSchema } from 'graphql';
import { pruneSchema } from '@graphql-tools/utils';

const DEFAULT_SCHEMA_PATH = '../../../../../schema.graphql';

async function executeSalesforceGraphQLQuery(query, variables, operationName) {
  const {
    rawInstanceUrl: instanceUrl,
    apiVersion,
    accessToken,
  } = await getOrgInfo();

  const targetUrl = `${instanceUrl}/services/data/v${apiVersion}/graphql`;

  console.log(`Executing introspection query against ${targetUrl}`);
  const response = await fetch(targetUrl, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      'X-Chatter-Entity-Encoding': 'false',
    },
    body: JSON.stringify({ query, variables, operationName }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Salesforce GraphQL request failed: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  return response.json();
}

try {
  const outputPath = resolve(process.argv[2] || DEFAULT_SCHEMA_PATH);

  const introspectionResult = await executeSalesforceGraphQLQuery(
    getIntrospectionQuery(),
    {},
    'IntrospectionQuery'
  );

  const schema = buildClientSchema(introspectionResult.data);
  const prunedSchema = pruneSchema(schema);
  const sdl = printSchema(prunedSchema);

  writeFileSync(outputPath, sdl);

  console.log(`Schema saved to ${outputPath}`);
} catch (error) {
  console.error('Error:', error.message);
  process.exit(1);
}
