# Barcode Scanner Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages barcode scanning facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the barcode scanning API of the mobile device, within the LWC.

## Barcode Scanner Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode BarcodeScanner}.
 * @returns An instance of {@linkcode BarcodeScanner}.
 */
export function getBarcodeScanner(): BarcodeScanner;

/**
 * Scan barcodes from a Lightning web component.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-barcodescanner.html|BarcodeScanner API}
 */
export interface BarcodeScanner extends BaseCapability {
  /**
   * @deprecated Use this function to start a new scanning session. Consider using scan() instead.
   * @param options A {@linkcode BarcodeScannerOptions} object to configure the scanning session.
   * @returns A resolved promise returns {@linkcode Barcode} object.
   */
  beginCapture(options?: BarcodeScannerOptions): Promise<Barcode>;

  /**
   * @deprecated Use this function to continue a scanning session. Consider using scan() instead.
   * @returns A resolved promise returns {@linkcode Barcode} object.
   */
  resumeCapture(): Promise<Barcode>;

  /**
   * @deprecated Use this function to end a scanning session, close the mobile OS scanning interface, and dispose resources. Consider using dismiss() instead.
   */
  endCapture(): void;

  /**
   * Use this function to start scanning barcodes.
   * @returns A resolved promise returns an array of {@linkcode Barcode} objects.
   */
  scan(options: BarcodeScannerOptions): Promise<Barcode[]>;

  /**
   * Use this function to end a scanning session, close the mobile OS scanning interface, and dispose of resources.
   */
  dismiss(): void;

  /**
   * Available values of barcode types as defined by {@linkcode BarcodeType}.
   */
  barcodeTypes: BarcodeType;
}

/**
 * An object representing a scanned barcode.
 */
export interface Barcode {
  /**
   * The type of barcode that was recognized. Available values are enumerated in BarcodeScanner.barcodeTypes.
   */
  type: BarcodeType;

  /**
   * The decoded value of the barcode.
   */
  value: string;
}

/**
 * An object enumerating the barcode symbologies supported by {@linkcode BarcodeScanner}.
 */
export interface BarcodeType {
  CODE_128: 'code128';
  CODE_39: 'code39';
  CODE_93: 'code93';
  DATA_MATRIX: 'datamatrix';
  EAN_13: 'ean13';
  EAN_8: 'ean8';
  ITF: 'itf';
  UPC_A: 'upca';
  UPC_E: 'upce';
  PDF_417: 'pdf417';
  QR: 'qr';
}

/**
 * An object representing an error that occurred when attempting to scan a barcode.
 */
export interface BarcodeScannerFailure {
  /**
   * A value representing the reason for the scanning failure
   */
  code: BarcodeScannerFailureCode;

  /**
   * A string value explaining the reason for the scanning failure.
   * This value is suitable for use in user interface messages.
   * The message is provided in English, and isn’t localized.
   */
  message: string;
}

/**
 * Possible failure codes.
 */
export type BarcodeScannerFailureCode =
  | 'USER_DISMISSED' // The user clicked the button to dismiss the scanner
  | 'USER_DENIED_PERMISSION' // This is only ever returned on android. android: permission was denied by user when prompt, could ask again.
  | 'USER_DISABLED_PERMISSION' // Both ios and android will use this as it requires the same action of the user going to settings.
  // Android: permission was denied along "don't ask again" when prompt, will need to go app setting to turn on.
  // iOS: permission was disabled by the user and will need to be turned on in settings
  | 'INVALID_BARCODE_TYPE_REQUESTED' // One or more invalid barcode types were passed to the scanner for scanning
  | 'SERVICE_NOT_ENABLED' // The service is not enabled and therefore cannot be used.
  | 'UNKNOWN_REASON'; //  A hardware or unknown failure happened when trying to use the camera or other reason, like FirebaseVision failure. This is not caused by a lack of permission.

/**
 * ScannerSize values.
 */
export type ScannerSize = 'SMALL' | 'MEDIUM' | 'LARGE' | 'XLARGE' | 'FULLSCREEN';

/**
 * CameraFacing values.
 */
export type CameraFacing = 'FRONT' | 'BACK';

/**
 * An object representing configuration details for a barcode scanning session.
 */
export interface BarcodeScannerOptions {
  /**
   * Optional. Specifies the types of barcodes to scan for. Available values are enumerated in BarcodeScanner.barcodeTypes. Defaults to all supported barcode types.
   */
  barcodeTypes?: string[];

  /**
   * Optional. Provides instructions to display in the scanning interface. Defaults to no text.
   */
  instructionText?: string;

  /**
   * Optional. Provides a message to display in the scanning interface when a barcode is successfully scanned. Defaults to no text.
   */
  successText?: string;

  /**
   * Optional. Indicates whether or not a check mark is displayed upon a successful scan. Defaults to true.
   */
  showSuccessCheckMark?: boolean;

  /**
   * Optional. Determines whether the device vibrates when a scan is successful. Defaults to true.
   */
  vibrateOnSuccess?: boolean;

  /**
   * Optional. Modifies the size of the scanner camera view. The available options represent a percentage of the user's device screen size.
   */
  scannerSize?: ScannerSize;

  /**
   * Optional. Specifies whether the front- or rear-facing camera is used. Defaults to "BACK". Available options include "FRONT" and "BACK". If the user's device doesn't support the specified camera facing, an error is returned.
   */
  cameraFacing?: CameraFacing;

  /**
   * Optional. Defines a custom user interface for the scanner instead of using the standard UI. Defaults to null. If nothing is passed in for this parameter, the standard UI is used. If a custom UI is used, it completely replaces the standard UI,
   * including the standard Cancel button used for dismissing the scanner. When defining a custom UI, it's the responsibility of the caller to handle dismissing the scanner.
   */
  backgroundViewHTML?: string;

  /**
   * Optional. Determines whether the scanner animates in and out when presented and dismissed. Defaults to true.
   */
  presentWithAnimation?: boolean;

  /**
   * Optional. Determines whether the user has to manually confirm that a detected barcode should be scanned. Defaults to false.
   */
  manualConfirmation?: boolean;

  /**
   * Optional. Determines whether the scanner displays the barcode data while scanning. Defaults to true. Previewing barcode is only supported when backgroundViewHTML is omitted.
   */
  previewBarcodeData?: boolean;

  /**
   * Optional. Determines whether the scanner collects the results of scanned barcodes before sending them back to the caller. Defaults to false. When set to true, the scanner
   * collects the results of scanned barcodes and displays them on the screen. When the user taps done, the scanned barcode data is sent back to the caller.
   */
  enableBulkScan?: boolean;

  /**
   * Optional. Determines whether the scanner detects multiple barcodes simultaneously. Defaults to false. Setting this parameter to true will automatically set the enableBulkScan parameter to true as well.
   */
  enableMultiScan?: boolean;

  /**
   * Optional. Enable flashlight. Defaults to false.
   */
  enableFlashlight?: boolean;

  /**
   * Optional. Defaults to 1.0 or 1x magnification. Sets the initial magnification level of the camera when launching the scanner.
   * A value of 1.0 represents no magnification (1x). Higher values (e.g., 2.0 or 4.0) can be useful for scanning small barcodes
   * without requiring manual zoom gestures. Users can still adjust the zoom level using pinch-to-zoom gestures.
   * Note: If the provided zoom factor exceeds the device camera's supported range, the value will be clamped to the nearest
   * supported min/max zoom factor.
   */
  initialZoomFactor?: number;
}
```
