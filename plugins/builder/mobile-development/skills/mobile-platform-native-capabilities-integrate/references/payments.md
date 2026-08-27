# Payments Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages payments facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the payments API of the mobile device, within the LWC.

## Payments Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode PaymentsService}.
 * @returns An instance of {@linkcode PaymentsService}.
 */
export function getPaymentsService(): PaymentsService;

/**
 * PaymentsService is a Nimbus plugin that allows JavaScript code in a Lightning web component to call functions that launches Stripe's Tap to Pay capabilities.
 */
export interface PaymentsService extends BaseCapability {
  /**
   * Process payment.
   * @param options The customization options.
   * @returns A Promise object that resolves to {@linkcode CollectPaymentResult} object.
   */
  collectPayment(options: CollectPaymentOptions): Promise<CollectPaymentResult>;

  /**
   * Get the supported payment methods on this device
   * @param options The customization options.
   * @returns  A Promise object that resolves to an array containing {@linkcode PaymentMethod} objects.
   */
  getSupportedPaymentMethods(options: GetSupportedPaymentMethodsOptions): Promise<PaymentMethod[]>;
}

/**
 * PaymentMethod values.
 */
export type PaymentMethod = 'TAP_TO_PAY' | 'CREDIT_CARD_DETAILS' | 'PAY_VIA_LINK';

/**
 * GetSupportedPaymentMethodsOptions interface.
 */
export interface GetSupportedPaymentMethodsOptions {
  countryIsoCode?: string;
  merchantAccountId?: string;
  permissionRationaleText?: string;
}

/**
 * CollectPaymentOptions interface.
 */
export interface CollectPaymentOptions {
  amount: number;
  paymentMethod: PaymentMethod;
  currencyIsoCode: string;
  merchantAccountId: string;
  merchantName: string;
  payerAccountId?: string;
  sourceObjectIds?: string[];
  permissionRationaleText?: string;
}

/**
 * CollectPaymentResult interface.
 */
export interface CollectPaymentResult {
  gatewayRefId?: string;
  guid?: string;
  paymentGatewayId?: string;
  status?: string;
}

/**
 * PaymentsServiceFailure interface.
 */
export interface PaymentsServiceFailure {
  code: PaymentsServiceFailureCode;
  message: string;
}

/**
 * Possible failure codes.
 */
export type PaymentsServiceFailureCode =
  | 'USER_DISMISSED' // User cancelled the operation.
  | 'USER_DENIED_PERMISSION' // Permission to access device location is denied.
  | 'SERVICE_NOT_ENABLED' // The service is not enabled and therefore cannot be used.
  | 'UNKNOWN_REASON'; // An error happened in the native code that is not permission based. Will give more information in the PaymentsServiceFailure message.
```
