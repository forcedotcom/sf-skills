/**
 * Copyright (c) 2026, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

interface SfdcEnv {
	/** Salesforce org force.com URL (e.g., "https://myorg.lightning.force.com"). */
	orgUrl?: string;
}

// eslint-disable-next-line no-var -- ambient global declaration
declare var SFDC_ENV: SfdcEnv | undefined;
