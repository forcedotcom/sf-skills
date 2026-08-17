/**
 * SObject adapter — the original uiapi GraphQL bridge, now behind the
 * kind-agnostic {@link SourceAdapter} contract.
 *
 * `buildRequest` delegates to the extracted fragment builder and
 * `parseResponse` to the extracted response parser. Both preserve the original
 * behaviour byte-for-byte; this file is only the wiring.
 */

import type { SObjectSourceConfig } from "../../types";
import type { SourceAdapter } from "../types";
import { buildSObjectFragment } from "./queryFragment";
import { parseSObjectResponse } from "./parseResponse";

export const sObjectAdapter: SourceAdapter<SObjectSourceConfig> = {
	kind: "sobject",
	buildRequest: buildSObjectFragment,
	parseResponse: parseSObjectResponse,
};
