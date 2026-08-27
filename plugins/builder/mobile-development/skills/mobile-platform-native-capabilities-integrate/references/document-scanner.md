# Document Scanner Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages document scanning facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the document scanner API of the mobile device, within the LWC.

## Document Scanner Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode DocumentScanner}.
 * @returns An instance of {@linkcode DocumentScanner}.
 */
export function getDocumentScanner(): DocumentScanner;

/**
 * Scan documents from a Lightning web component.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-documentscanner.html|DocumentScanner API}
 */
export interface DocumentScanner extends BaseCapability {
  /**
   * Use this function to start scanning a document.
   * @param options A {@linkcode DocumentScannerOptions} object to configure the scanning session.
   * @returns A Promise object that resolves to an array containing one or more {@linkcode Document} objects.
   */
  scan(options?: DocumentScannerOptions): Promise<Document[]>;
}

/**
 * An object representing a scanned document. Returned as the result of a successful scan operation.
 */
export interface Document {
  /**
   * A string containing the base64 image data of the scanned document. Only provided when returnImageBytes is set to true in your {@linkcode DocumentScannerOptions} configuration object.
   */
  imageBytes?: string;

  /**
   * A string value providing the recognized text from the scanned document.
   */
  text: string;

  /**
   * An array of {@linkcode TextBlock} objects that represent a structured text result that is visually aligned with the corresponding image. See {@linkcode TextBlock} for details of this structured text data.
   */
  blocks: TextBlock[];

  /**
   * An array of {@linkcode Entity} objects.
   */
  entities: Entity[];
}

/**
 * An object representing a contiguous section of the scanned text. Text that is visually close together is grouped into a block of text.
 * A document is made up of one to many blocks, and each block can be further broken down into smaller text elements: {@linkcode TextLine} (a single line of text in
 * a visually aligned run of text) and {@linkcode TextElement} (an individual word or glyph).
 */
export interface TextBlock {
  /**
   * A string containing the text content of the block.
   */
  text: string;

  /**
   * An object containing the coordinates — position and size — that represent the bounding rectangle in the scanned image that contains the {@linkcode TextBlock}.
   */
  frame: Frame;

  /**
   * An array of Point objects that define a closed shape within the scanned image that contains the {@linkcode TextBlock}.
   */
  cornerPoints: Point[];

  /**
   * The BCP-47 language code values for the languages detected in the recognized text.
   */
  recognizedLangCodes: string[];

  /**
   * An array of {@linkcode TextLine} objects, each of which represents a visually aligned line of text within the {@linkcode TextBlock}.
   */
  lines: TextLine[];
}

/**
 * An object representing a single line of scanned text.
 */
export interface TextLine {
  /**
   * A string containing the text content of the line.
   */
  text: string;

  /**
   * An object containing the coordinates — position and size — that represent the bounding rectangle in the scanned image that contains the {@linkcode TextLine}.
   */
  frame: Frame;

  /**
   * An array of {@linkcode Point} objects that define a closed shape within the scanned image that contains the {@linkcode TextLine}.
   */
  cornerPoints: Point[];

  /**
   * The BCP-47 language code values for the languages detected in the recognized text.
   */
  recognizedLangCodes: string[];

  /**
   * An array of {@linkcode TextElement} objects, each of which represents a word or glyph within the {@linkcode TextLine}.
   */
  elements: TextElement[];
}

/**
 * An object representing a single word, individual character, or glyph.
 */
export interface TextElement {
  /**
   * A string containing the text content of the word or character.
   */
  text: string;

  /**
   * An object containing the coordinates — position and size — that represent the bounding rectangle in the scanned image that contains the {@linkcode TextElement}.
   */
  frame: Frame;

  /**
   * An array of {@linkcode Point} objects that define a closed shape within the scanned image that contains the {@linkcode TextElement}.
   */
  cornerPoints: Point[];

  /**
   * The BCP-47 language code values for the languages detected in the recognized text.
   */
  recognizedLangCodes: string[];
}

/**
 * An object representing a bounding rectangle. When used in {@linkcode DocumentScanner}, the Frame is the smallest that fully encloses a region of scanned text for a {@linkcode TextBlock}, {@linkcode TextLine}, or {@linkcode TextElement}.
 */
export interface Frame {
  /**
   * The X coordinate of the top-left of the rectangle, in pixels, within the coordinate system of the scanned image.
   */
  x: number;

  /**
   * The Y coordinate of the top-left of the rectangle, in pixels, within the coordinate system of the scanned image.
   */
  y: number;

  /**
   * The width of the rectangle, in pixels.
   */
  width: number;

  /**
   * The height of the rectangle, in pixels.
   */
  height: number;
}

/**
 * An object representing a point in a coordinate system.
 */
export interface Point {
  /**
   * The X coordinate of the point.
   */
  x: number;

  /**
   * The Y coordinate of the point.
   */
  y: number;
}

/**
 * Entity interface.
 */
export interface Entity {
  type: EntityType;
  value: string;
  dateTimeEntity?: DateTimeEntity;
  flightNumberEntity?: FlightNumberEntity;
  ibanEntity?: IBANEntity;
  moneyEntity?: MoneyEntity;
  paymentCardEntity?: PaymentCardEntity;
  trackingNumberEntity?: TrackingNumberEntity;
}

/**
 * EntityType values.
 */
export type EntityType =
  | 'ADDRESS'
  | 'DATETIME'
  | 'EMAIL'
  | 'FLIGHTNUMBER'
  | 'IBAN'
  | 'ISBN'
  | 'MONEY'
  | 'PAYMENTCARD'
  | 'PHONE'
  | 'TRACKINGNUMBER'
  | 'URL';

/**
 * DateTimeEntity interface.
 */
export interface DateTimeEntity {
  secondsUTC: number;
  granularity: string;
}

/**
 * FlightNumberEntity interface.
 */
export interface FlightNumberEntity {
  airlineCode: string;
  flightNumber: string;
}

/**
 * IBANEntity interface.
 */
export interface IBANEntity {
  countryCode: string;
  iban: string;
}

/**
 * MoneyEntity interface.
 */
export interface MoneyEntity {
  unnormalizedCurrency: string;
  integerPart: number;
  fractionalPart: number;
}

/**
 * PaymentCardEntity interface.
 */
export interface PaymentCardEntity {
  network: string;
  cardNumber: string;
}

/**
 * TrackingNumberEntity interface.
 */
export interface TrackingNumberEntity {
  carrier: string;
  trackingNumber: string;
}

/**
 * DocumentScannerSource values.
 */
export type DocumentScannerSource = 'INPUT_IMAGE' | 'PHOTO_LIBRARY' | 'DEVICE_CAMERA';

/**
 * Script values.
 */
export type Script = 'CHINESE' | 'DEVANAGARI' | 'JAPANESE' | 'KOREAN' | 'LATIN';

/**
 * An object containing configuration details for a document scanning session.
 */
export interface DocumentScannerOptions {
  /**
   * Optional, and only for Android implementations. The text shown in the UI when the device prompts the user to grant permission for your app to use the camera.
   */
  permissionRationaleText?: string;

  /**
   * Optional. Specifies the source of the document to be scanned. Defaults to "DEVICE_CAMERA".
   */
  imageSource?: DocumentScannerSource;

  /**
   * Optional. Specifies the language writing system of the text to be scanned. Defaults to "LATIN".
   */
  scriptHint?: Script;

  /**
   * Defaults to FALSE when omitted.
   */
  extractEntities?: boolean;

  /**
   * Defaults to EN when omitted.
   */
  entityExtractionLanguageCode?: string;

  /**
   * Optional. Specifies whether the image data should (true) or should not (false) be returned by the plugin. Defaults to false. This setting is overridden and set to false when imageSource is set to “INPUT_IMAGE”.
   */
  returnImageBytes?: boolean;

  /**
   * Optional. A stringified array of base64 image data to be scanned. Used when imageSource is set to "INPUT_IMAGE".
   */
  inputImageBytes?: string[];
}

/**
 * An object representing an error that occurred when accessing {@linkcode DocumentScanner} features.
 */
export interface DocumentScannerFailure {
  /**
   * A value representing the reason for a document scanner error. See {@linkcode DocumentScannerFailureCode} for the list of possible values.
   */
  code: DocumentScannerFailureCode;

  /**
   * A string value describing the reason for the failure. This value is suitable for use in user interface messages. The message is provided in English and isn’t localized.
   */
  message: string;
}

/**
 * Correlates with the code property on the {@linkcode DocumentScannerFailure} object.
 */
export type DocumentScannerFailureCode =
  | 'USER_DISMISSED' // User dismissed the scanner.
  | 'USER_DENIED_CAMERA_PERMISSION' // A user denied permission to access the device camera when prompted.
  | 'USER_DENIED_PHOTO_LIBRARY_PERMISSION' // A user denied permission to access the device photo library when prompted.
  | 'NO_SUPPORTED_CAMERA' // The device doesn’t have a supported camera.
  | 'INVALID_INPUT_IMAGE' // The input image data can’t be read as an image.
  | 'SERVICE_NOT_ENABLED' // DocumentScanner is not enabled and cannot be used.
  | 'UNKNOWN_REASON'; // An error occurred in the native code that isn’t related to permissions or hardware issues. More information is provided in the DocumentScannerFailure message.
```
