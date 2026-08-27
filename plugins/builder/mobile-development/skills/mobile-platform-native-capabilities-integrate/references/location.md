# Location Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages location facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the location API of the mobile device, within the LWC.

## Location Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode LocationService}.
 * @returns An instance of {@linkcode LocationService}.
 */
export function getLocationService(): LocationService;

/**
 * Access and track location in a Lightning web component.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-locationservice.html|LocationService API}
 */
export interface LocationService extends BaseCapability {
  /**
   * Gets the device’s current geolocation.
   * @param options A {@linkcode LocationServiceOptions} object to configure the location request.
   * @returns A Promise object that resolves as a {@linkcode LocationResult} object with the device location details.
   */
  getCurrentPosition(options?: LocationServiceOptions): Promise<LocationResult>;

  /**
   * Subscribes to asynchronous location updates for the mobile device.
   * @param options A {@linkcode LocationServiceOptions} object to configure the location request.
   * @param callback A function to handle location update responses.
   * @returns An integer identifier for the location subscription, which you can use to end the subscription when you want to stop receiving location updates.
   */
  startWatchingPosition(
    options: LocationServiceOptions | null,
    callback: (result?: LocationResult, failure?: LocationServiceFailure) => void,
  ): number;

  /**
   * Unsubscribes from location updates for the mobile device.
   * @param watchId An integer identifier for an active location subscription, returned by a call to startWatchingPosition().
   */
  stopWatchingPosition(watchId: number): void;
}

/**
 * LocationResult interface.
 */
export interface LocationResult {
  /**
   * The physical location.
   */
  coords: Coordinates;

  /**
   * The time of the location reading, measured in milliseconds since January 1, 1970.
   */
  timestamp: number;
}

/**
 * An object representing a specific point located on the planet Earth. Includes velocity details, if available.
 * Includes accuracy information, to the best of the device’s ability to evaluate. Similar to a GeolocationCoordinates in the Geolocation Web API.
 */
export interface Coordinates {
  /**
   * The latitude, in degrees. Ranges from -90 to 90.
   */
  latitude: number;

  /**
   * The longitude, in degrees. Ranges from -180 to 180.
   */
  longitude: number;

  /**
   * Optional. Accuracy of the location measurement, in meters, as a radius around the measurement.
   */
  accuracy?: number;

  /**
   * Optional. Meters above sea level.
   */
  altitude?: number;

  /**
   * Optional. Accuracy of the altitude measurement, in meters.
   */
  altitudeAccuracy?: number;

  /**
   * Optional. Velocity of motion, if any, in meters per second.
   */
  speed?: number;

  /**
   * Optional. Accuracy of the speed measurement, in meters.
   */
  speedAccuracy?: number;

  /**
   * Optional. Direction of motion, in degrees from true north. Ranges from 0 to 360.
   */
  heading?: number;

  /**
   * Optional. Accuracy of the heading measurement, in degrees.
   */
  headingAccuracy?: number; // accuracy for the heading in degree
}

/**
 * An object representing an error that occurred when accessing LocationService features.
 */
export interface LocationServiceFailure {
  /**
   * A value representing the reason for a location error.
   */
  code: LocationServiceFailureCode;

  /**
   * A string value explaining the reason for the failure. This value is suitable for use in user interface messages. The message is provided in English, and isn’t localized.
   */
  message: string;
}

/**
 * Possible failure codes.
 */
export type LocationServiceFailureCode =
  | 'LOCATION_SERVICE_DISABLED' // Android only - The code when the location service is disabled on the device, not just for this app.
  | 'USER_DENIED_PERMISSION' // Permission was denied by user when prompt, could ask again
  | 'USER_DISABLED_PERMISSION' // Android: permission was denied along "don't ask again" when prompt, will need to go app setting to turn on. iOS: permission was disabled by the user and will need to be turned on in settings
  | 'SERVICE_NOT_ENABLED' // The service is not enabled and therefore cannot be used.
  | 'UNKNOWN_REASON'; // An error happened in the Native Code that is not permission based. Will give more information in the LocationServiceFailure message.

/**
 * An object representing configuration details for a location service session.
 */
export interface LocationServiceOptions {
  /**
   * Whether to use high accuracy mode when determining location. Set to true to prioritize location accuracy.
   * Set to false to prioritize battery life and response time.
   */
  enableHighAccuracy: boolean;

  /**
   * Optional, and only for Android implementations. The text shown in the UI when the device prompts the user to grant permission for your app to use the Android's location service.
   */
  permissionRationaleText?: string;
}
```
