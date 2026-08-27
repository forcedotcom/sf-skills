# NFC Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages NFC facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the NFC API of the mobile device, within the LWC.

## NFC Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode NfcService}.
 * @returns An instance of {@linkcode NfcService}.
 */
export function getNfcService(): NfcService;

/**
 * Interact with NFC tags from a Lightning web component.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-nfcservice.html|NFCService API}
 */
export interface NfcService extends BaseCapability {
  /**
   * Reads an NFC tag and returns the data read from it.
   * @param options An {@linkcode NFCServiceOptions} object to configure the {@linkcode NfcService} request.
   * @returns A Promise object that resolves to an array containing a single {@linkcode NFCMessage} object.
   */
  read(options?: NFCServiceOptions): Promise<NFCMessage[]>;

  /**
   * Erase the contents of an NFC tag.
   * @param options An {@linkcode NFCServiceOptions} object to configure the {@linkcode NfcService} request.
   * @returns If successful, the OS returns a Promise object that resolves to null.
   */
  erase(options?: NFCServiceOptions): Promise<null>;

  /**
   * Write text to an NFC tag.
   * @param payloads An array of {@linkcode NFCRecord} objects containing the raw bytes to be written.
   * @param options An {@linkcode NFCServiceOptions} object to configure the {@linkcode NfcService} request.
   * @returns If successful, the OS returns a Promise object that resolves to null.
   */
  write(payloads: NFCRecord[], options?: NFCServiceOptions): Promise<null>;

  /**
   * Given a text payload, this function creates a properly formatted {@linkcode NFCRecord} to be written to an NFC tag.
   * @param payload A {@link TextPayload} object, which contains the text to be converted to an NFC record.
   * @returns A Promise object that resolves to an {@linkcode NFCRecord} object.
   */
  createTextRecord(payload: TextPayload): Promise<NFCRecord>;

  /**
   * Given a URI string payload, this function creates a properly formatted {@linkcode NFCRecord} to be written to an NFC tag.
   * @param payload The URI to be converted to an NFC record.
   * @returns A Promise object that resolves to an {@linkcode NFCRecord} object.
   */
  createUriRecord(payload: string): Promise<NFCRecord>;
}

/**
 * An object returned by an NFC read() operation.
 */
export interface NFCMessage {
  /**
   * The size, in number of bytes, of the data received by the read() operation.
   */
  totalByteLength: number;

  /**
   * An array containing a single {@linkcode NFCMessageRecord} object, which in turn contains the payload from the NFC tag.
   */
  records: NFCMessageRecord[];

  /**
   * An object containing a single {@linkcode NFCTagInfo} object, which in turn contains the matadata of the NFC tag.
   */
  tagInfo: NFCTagInfo;
}

/**
 * An object within an {@linkcode NFCMessage} object, containing the metadata read from an NFC tag.
 */
export interface NFCTagInfo {
  /**
   * The serial number of the tag
   */
  serialNumber: string;

  /**
   * Optional. For a tag that can contain NDEF data, this property indicates whether the tag's NDEF data can be overwritten.
   * If the tag does not support NDEF, the value of this property will be null.
   */
  isNdefWritable?: boolean | undefined;

  /**
   * Optional. The maximum NDEF message size in bytes that the tag can hold. If the tag does not support NDEF, the value of this property will be null.
   */
  ndefCapacity?: number | undefined;
}

/**
 * An object within an {@linkcode NFCMessage} object, containing the payload read from an NFC tag.
 */
export interface NFCMessageRecord {
  /**
   * Contains the parsed values of the raw data read from the NFC tag. The parsing operation
   * only occurs if the value of the typeNameFormat property on the {@linkcode NFCRecord} object is "WELLKNOWN".
   * Otherwise, this property’s value is null.
   */
  parsed: NFCRecord;

  /**
   * Contains the raw base64 data string read from the NFC tag.
   */
  raw: NFCRecord;
}

/**
 * An object containing one record of data from an NFC tag scan.
 */
export interface NFCRecord {
  /**
   * The Type Name Format field of the payload, as defined by the NDEF specification.
   */
  typeNameFormat: TypeNameFormat;

  /**
   * The type of the payload, as defined by the NDEF specification.
   */
  type: string;

  /**
   * The identifier of the payload, as defined by the NDEF specification, or an empty string if no identifier data was present in the tag.
   */
  identifier: string;

  /**
   * The content of the record, encoded in base64 format.
   */
  payload: string;
}

/**
 * An object containing raw text input, to be converted into an {@linkcode NFCRecord}.
 */
export interface TextPayload {
  /**
   * The raw text payload to be converted.
   */
  text: string;

  /**
   * The ISO 639-1 language ID of the text.
   */
  langId: string;
}

/**
 * The following constants are available as properties on an instance of {@linkcode NfcService}. The constants enumerate the accepted values for the associated properties.
 */
export type TypeNameFormat = 'ABSOLUTE_URI' | 'EMPTY' | 'EXTERNAL' | 'MEDIA' | 'WELLKNOWN' | 'UNCHANGED' | 'UNKNOWN';

/**
 * An object containing configuration details for an NFC interaction.
 */
export interface NFCServiceOptions {
  /**
   * Optional. Indicates whether reading from an empty tag should be considered an error or not.
   * Defaults to FALSE, so attempting to read an empty tag will return TAG_EMPTY error.
   * If you want to get back the tag metadata even for empty tags, you should set this property to TRUE,
   * so that instead of TAG_EMPTY error, the read() operation would return an {@linkcode NFCMessage} object
   * where its {@linkcode NFCTagInfo} is populated.
   */
  allowEmptyTags?: boolean;

  /**
   * Optional. Provides instructions to display in the user interface. Defaults to no text.
   */
  instructionText?: string;

  /**
   * Optional. Provides a message to display in the user interface when an NFC operation is successfully completed. Defaults to no text.
   */
  successText?: string;
}

/**
 * An object representing an error that occurred when accessing {@linkcode NfcService} features.
 */
export interface NFCServiceFailure {
  /**
   * A value representing the reason for an error. See {@linkcode NFCServiceFailureCode} for the list of possible values.
   */
  code: NFCServiceFailureCode;

  /**
   * A string value describing the reason for the failure. This value is suitable for use in user interface messages. The message is provided in English and isn’t localized.
   */
  message: string;
}

/**
 * Correlates with the code property on the {@linkcode NFCServiceFailure} object.
 */
export type NFCServiceFailureCode =
  | 'USER_DISMISSED' // The user dismissed the scanner.
  | 'NFC_NOT_SUPPORTED' // The device doesn’t support NFC capabilities.
  | 'NFC_NOT_ENABLED' // The device NFC feature is turned off.
  | 'TAG_EMPTY' // The NFC tag contains no data to be read.
  | 'SERVICE_NOT_ENABLED' // NFCService is not enabled and cannot be used.
  | 'UNKNOWN_REASON'; // An error occurred in the native code that isn’t related to permissions or hardware issues. More information is provided in the NFCServiceFailure message.
```
