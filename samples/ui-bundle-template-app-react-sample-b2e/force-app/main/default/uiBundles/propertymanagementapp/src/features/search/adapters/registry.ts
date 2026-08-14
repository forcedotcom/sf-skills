/**
 * Adapter registry — maps a source `kind` to its runtime {@link SourceAdapter}.
 *
 * The core query builder and response parser call {@link getAdapter} for each
 * source instead of hard-coding SObject logic, so a new backend is added purely
 * by registering an adapter here (plus its `kind` in the `SourceConfig` union).
 *
 * The `cmsAdapter` is authored by the CMS implementer at `./cms` (exported as
 * `cmsAdapter`); it is imported and registered here, never stubbed.
 */

import type { SourceConfig } from "../types";
import type { SourceAdapter } from "./types";
import { sObjectAdapter } from "./sobject";
import { cmsAdapter } from "./cms";

/**
 * Registry keyed by `SourceConfig["kind"]`. Each entry is the adapter narrowed
 * to the matching config variant; `getAdapter` widens back to the base
 * `SourceAdapter` for kind-agnostic callers.
 */
const REGISTRY: { [K in SourceConfig["kind"]]: SourceAdapter<Extract<SourceConfig, { kind: K }>> } =
	{
		sobject: sObjectAdapter,
		cms: cmsAdapter,
	};

/**
 * Returns the adapter registered for `kind`. Throws on an unknown kind (a
 * config carrying a `kind` with no adapter is a programming error).
 */
export function getAdapter(kind: SourceConfig["kind"]): SourceAdapter {
	const adapter = REGISTRY[kind];
	if (!adapter) {
		throw new Error(`No search adapter registered for source kind "${kind}".`);
	}
	return adapter as SourceAdapter;
}
