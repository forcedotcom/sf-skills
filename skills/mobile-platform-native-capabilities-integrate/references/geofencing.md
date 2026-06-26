# Geofencing Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages geofencing facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the geofencing API of the mobile device, within the LWC.

## Geofencing Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode GeofencingService}.
 * @returns An instance of {@linkcode GeofencingService}.
 */
export function getGeofencingService(): GeofencingService;

/**
 * Create and monitor geofences in a Lightning web component.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-geofencingservice.html|GeofencingService API}
 */
export interface GeofencingService extends BaseCapability {
  /**
   * Starts geofence monitoring.
   * @param geofence A {@linkcode Geofencing} object to monitor.
   * @returns A Promise object that resolves as a string value. The value is a unique ID that’s assigned to the monitored geofence.
   */
  startMonitoringGeofence(geofence: Geofence): Promise<string>;

  /**
   * Stop monitoring a specific geofence.
   * @param id  Unique ID assigned to a specific geofence.
   * @returns A Promise object that resolves as null.
   */
  stopMonitoringGeofence(id: string): Promise<null>;

  /**
   * Stop monitoring all geofences.
   * @returns A Promise object that resolves as null.
   */
  stopMonitoringAllGeofences(): Promise<null>;

  /**
   * Get all IDs of monitored geofences.
   * @returns A Promise object that resolves as an array of string values. The values are unique IDs assigned to monitored geofences.
   */
  getMonitoredGeofences(): Promise<string[]>;
}

/**
 * An object representing an error that occurred when accessing {@linkcode GeofencingService} features.
 */
export interface GeofencingServiceFailure {
  /**
   * A value representing the reason for a location error.
   */
  code: GeofencingServiceFailureCode;

  /**
   * A string value explaining the reason for the failure. This value is
   * suitable for use in user interface messages. The message is provided in English and isn’t localized.
   */
  message: string;
}

/**
 * Possible failure codes.
 */
export type GeofencingServiceFailureCode =
  | 'LOCATION_SERVICE_DISABLED' // Android Only: The location service is disabled on the device, not just for this app.
  | 'USER_DENIED_PERMISSION' // Permission was denied by user when prompt, could ask again
  | 'USER_DISABLED_PERMISSION' // Android: permission was denied along "don't ask again" when prompt, will need to go app setting to turn on. iOS: permission was disabled by the user and will need to be turned on in settings
  | 'UNAVAILABLE_ON_HARDWARE' // Geofence monitoring not available on the hardware.
  | 'MAX_GEOFENCE_MONITORED_REACHED' // The maximum number of geofences that can be monitored by the OS has been reached.
  | 'INVALID_LATITUDE' // The range of latitude for a geofence is -90...90
  | 'INVALID_LONGITUDE' // The range of longitude for a geofence is -180...180
  | 'SERVICE_NOT_ENABLED' // The service is not enabled and therefore cannot be used.
  | 'UNKNOWN_REASON'; // An error happened in the Native Code that is not permission based. Will give more information in the GeofencingServiceFailure message.

/**
 * An object representing the coordinates and radius of the geofence region.
 */
export interface Geofence {
  /**
   * The latitude, in degrees. Ranges from -90 to 90.
   */
  latitude: number;

  /**
   * The longitude, in degrees. Ranges from -180 to 180.
   */
  longitude: number;

  /**
   * The radius of the geofence in meters.
   */
  radius: number;

  /**
   * Monitors the entry into the geofence radius. Defaults to true.
   */
  notifyOnEntry: boolean;

  /**
   * Monitors the exit out of the geofence radius. Defaults to true.
   */
  notifyOnExit: boolean;

  /**
   * Notification triggered by a geofence event.
   */
  message: string;

  /**
   * Removes geofence after it’s triggered. Defaults to true.
   */
  triggerOnce: boolean;
}
```
