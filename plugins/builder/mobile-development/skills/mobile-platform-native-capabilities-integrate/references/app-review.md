# App Review Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages app review facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the app review API of the mobile device, within the LWC.

## App Review Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode AppReviewService}.
 * @returns An instance of {@linkcode AppReviewService}.
 */
export function getAppReviewService(): AppReviewService;

/**
 * Request an app review from a Lightning web component.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-appreviewservice.html|AppReviewService API}
 */
export interface AppReviewService extends BaseCapability {
  /**
   * Requests an app review.
   * @param options An {@linkcode AppReviewServiceOptions} object to configure the {@linkcode AppReviewService} request.
   * @returns A resolved promise returns null.
   */
  requestAppReview(options?: AppReviewServiceOptions): Promise<null>;
}

/**
 * An object representing configuration details for an {@linkcode AppReviewService} session.
 */
export interface AppReviewServiceOptions {
  /**
   * Ignore the app review request if already asked for the current version of the app.
   */
  ignoreIfAlreadyRequestedForCurrentAppVersion: boolean;
}

/**
 * An object representing an error that occurred when accessing {@linkcode AppReviewService} features.
 */
export interface AppReviewServiceFailure {
  /**
   * A value representing the reason for an app review error.
   */
  code: AppReviewServiceFailureCode;

  /**
   * A string value describing the reason for the failure. This value is suitable for use in user interface messages. The message is provided in English and isn’t localized.
   */
  message: string;
}

/**
 * Possible failure codes.
 */
type AppReviewServiceFailureCode =
  | 'ALREADY_REQUESTED_FOR_CURRENT_APP_VERSION'
  | 'IN_APP_REVIEW_ERROR'
  | 'SERVICE_NOT_ENABLED'
  | 'UNKNOWN_REASON';
```
