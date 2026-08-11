/**
 * Typed re-export of the static config.json that ships with the feature.
 *
 * Application code:
 *   import { config } from ".../features/search/loadConfig";
 *   const handle = useSearch(config);
 *
 * To customize, edit `config.json` directly (no code changes required).
 */

import rawConfig from "./config.json";
import type { SearchConfig } from "./types";

export const config: SearchConfig = rawConfig as SearchConfig;
