/**
 * Builds a single combined GraphQL document for search across every source.
 *
 * The builder is kind-agnostic: for each source request it asks the registered
 * adapter (`getAdapter(kind).buildRequest`) for a `QueryFragmentContribution`
 * and assembles them:
 *   - `placement: "uiapi.query"` fragments (e.g. SObject sources) go inside the
 *     shared `uiapi { query { … } }` block.
 *   - `placement: "root"` fragments (e.g. the CMS `managed_content` block) go in
 *     as siblings of `uiapi` at the document root.
 *   - every contribution's `variableDeclarations` are concatenated into the
 *     `query Search(...)` header and every contribution's `variables` merged
 *     into one flat map.
 *
 * A contribution may declare zero extra variables (the CMS bootstrap call omits
 * `$cmsContentTypeFQNs` entirely), so the merge tolerates declaration lists of
 * differing lengths and never emits a declared-but-unused variable.
 *
 * When only SObject sources participate, the emitted document is identical to
 * the pre-adapter builder — the `uiapi` block is unchanged and no root siblings
 * are added.
 */

import { getAdapter } from "./adapters/registry";
import type { SourceRequest } from "./adapters/types";

// `SourceRequest` is now defined canonically in `adapters/types.ts`; re-export
// it here for backward compatibility (the barrel and existing consumers import
// `SourceRequest` from `./queryBuilder`).
export type { SourceRequest } from "./adapters/types";

export interface SearchQueryPayload {
	document: string;
	variables: Record<string, unknown>;
}

/**
 * Builds the combined query document and a flat variables map by dispatching
 * each source through its adapter and partitioning fragments by placement.
 */
export function buildSearchQuery(requests: SourceRequest[]): SearchQueryPayload {
	if (requests.length === 0) {
		throw new Error("buildSearchQuery requires at least one source request");
	}

	const variableDeclarations: string[] = [];
	const uiapiFragments: string[] = [];
	const rootFragments: string[] = [];
	const variables: Record<string, unknown> = {};

	for (const request of requests) {
		const contribution = getAdapter(request.source.kind).buildRequest(request);

		// Concatenate declarations (may be empty for a given source) and merge
		// values — an omitted declaration means the variable is never declared,
		// so it is likewise never supplied.
		variableDeclarations.push(...contribution.variableDeclarations);
		Object.assign(variables, contribution.variables);

		if (contribution.placement === "root") {
			rootFragments.push(contribution.fragment);
		} else {
			uiapiFragments.push(contribution.fragment);
		}
	}

	const parts: string[] = [`query Search(${variableDeclarations.join(", ")}) {`];

	// The `uiapi { query { … } }` block holds every `uiapi.query`-placed fragment.
	// Emit it only when at least one such fragment exists — a CMS-only request
	// (all SObject sources dropped) must not produce an empty, invalid selection
	// set. When SObject sources are present its shape is identical to the
	// pre-adapter builder.
	if (uiapiFragments.length > 0) {
		parts.push(`  uiapi {`);
		parts.push(`    query {`);
		parts.push(uiapiFragments.map((s) => indent(s, "      ")).join("\n"));
		parts.push(`    }`);
		parts.push(`  }`);
	}

	// Root-placement fragments (e.g. CMS `managed_content`) are siblings of uiapi.
	for (const fragment of rootFragments) {
		parts.push(indent(fragment, "  "));
	}

	parts.push(`}`);

	// Trailing newline preserved from the original builder.
	const document = parts.join("\n") + "\n";

	return { document, variables };
}

function indent(s: string, prefix: string): string {
	return s
		.split("\n")
		.map((line) => prefix + line)
		.join("\n");
}
