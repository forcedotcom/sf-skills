# lightning/mobileCapabilities

Module declaration that re-exports every native capability service. Import the factory functions from `lightning/mobileCapabilities` (or the per-service path) when authoring an LWC.

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

/**
 * Mobile capabilities are JavaScript APIs that make mobile hardware and platform (operating system) features available in JavaScript. They require access to device hardware, platform APIs, or both.
 * Mobile capability APIs are available only when a Lightning web component runs in a supported mobile app on a mobile device.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-mobilecapabilities.html|lightning/mobileCapabilities Module}
 */
declare module 'lightning/mobileCapabilities' {
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/AppReviewService/appReviewService.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/ARSpaceCapture/arSpaceCapture.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/BarcodeScanner/barcodeScanner.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/BiometricsService/biometricsService.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/CalendarService/calendarService.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/ContactsService/contactsService.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/DocumentScanner/documentScanner.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/GeofencingService/geofencingService.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/LocationService/locationService.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/NfcService/nfcService.js';
  export * from '@salesforce/lightning-types/dist/lightning/mobileCapabilities/PaymentsService/paymentsService.js';
}
```
