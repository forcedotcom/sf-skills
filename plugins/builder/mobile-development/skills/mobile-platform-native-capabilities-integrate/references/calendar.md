# Calendar Service Grounding Context

The following content provides grounding information for generating a Salesforce LWC that leverages calendar facilities on mobile devices. Specifically, this context will cover the API types and methods available to leverage the calendar API of the mobile device, within the LWC.

## Calendar Service API

```typescript
/*
 * Copyright (c) 2024, Salesforce, Inc.
 * All rights reserved.
 * For full license text, see the LICENSE.txt file
 */

import { BaseCapability } from '../BaseCapability.js';

/**
 * Use this factory function to get an instance of {@linkcode CalendarService}.
 * @returns An instance of {@linkcode CalendarService}.
 */
export function getCalendarService(): CalendarService;

/**
 * Manage calendar events from a Lightning web component.
 * @see {@link https://developer.salesforce.com/docs/platform/lwc/guide/reference-lightning-calendarservice.html|CalendarService API}
 */
export interface CalendarService extends BaseCapability {
  /**
   * Returns all available calendars from the device’s native Calendar application.
   * If needed, a permission pop-up for the user to grant calendar access is presented first.
   * @param options A {@linkcode CalendarServiceOptions} object to configure the {@linkcode CalendarService} request.
   * @returns A Promise object that resolves as an array of {@linkcode Calendar} objects.
   */
  getCalendars(options?: CalendarServiceOptions): Promise<Calendar[]>;

  /**
   * Returns all events of all available calendar events in a specified date range from the specified calendars.
   * @param startDateSecondsUTC The start of the date range.
   * @param endDateSecondsUTC The end of the date range.
   * @param calendars The titles of calendars to get events from. If not provided, or null is passed in, events are fetched from all available calendars.
   * @param options A {@linkcode CalendarServiceOptions} object to configure the {@linkcode CalendarService} request.
   * @returns A Promise object that resolves as an array of {@linkcode CalendarEvent} objects.
   */
  getEvents(
    startDateSecondsUTC: number,
    endDateSecondsUTC: number,
    calendars?: string[],
    options?: CalendarServiceOptions,
  ): Promise<CalendarEvent[]>;

  /**
   * Adds an event to the device’s calendar.
   * @param event A {@linkcode CalendarEvent} object to be added to the device’s calendar.
   * @param options A {@linkcode CalendarServiceOptions} object to configure the {@linkcode CalendarService} request.
   * @returns A Promise object that resolves as a coerced version of the {@linkcode CalendarEvent} parameter.
   */
  addEvent(event: CalendarEvent, options?: CalendarServiceOptions): Promise<CalendarEvent>;

  /**
   * Updates an event in the device’s calendar.
   * @param updatedEvent A {@linkcode CalendarEvent} object with updated data to replace the existing data in the corresponding event on the device’s calendar.
   * @param options A {@linkcode CalendarServiceOptions}  object to configure the {@linkcode CalendarService}  request.
   * @returns A Promise object that resolves as a coerced version of the {@linkcode CalendarEvent} parameter.
   */
  updateEvent(updatedEvent: CalendarEvent, options?: CalendarServiceOptions): Promise<CalendarEvent>;

  /**
   * Removes an event from a device’s calendar.
   * @param event The {@linkcode CalendarEvent} object to be removed from the device’s calendar.
   * @param options A {@linkcode CalendarServiceOptions} object to configure the {@linkcode CalendarService} request.
   * @returns If successful, null is returned.
   */
  removeEvent(event: CalendarEvent, options?: CalendarServiceOptions): Promise<null>;
}

/**
 * Calendar interface.
 */
export interface Calendar {
  id: string;
  title: string;
  allowsContentModifications: boolean; // indicates whether the calendar is read-only
  hexColor: string; // includes # + hex color value, e.g #c603fc
  type: string; // a string hinting about calendar type. It is platform specific. on iOS it is set to EKSource.sourceType+EKSource.title and on Android it is set to CalendarContract.Calendars.ACCOUNT_TYPE+CalendarContract.Calendars.ACCOUNT_NAME
  isPrimary: boolean; // indicates whether it is the primary/default calendar
}

/**
 * Event interface.
 */
export interface CalendarEvent {
  id: string;
  isAllDay: boolean; // defaults to False
  startDateSecondsUTC: number;
  endDateSecondsUTC: number;
  availability: EventAvailability; // defaults to Busy
  status: EventStatus; // read-only - value set by caller will be ignored and overwritten by the plugin
  calendarId?: string;
  title: string;
  location?: string;
  notes?: string;
  alarms?: Alarm[];
  attendees?: Participant[]; // Note: on iOS this field can only be used for fetching attendee info of an existing event, but you cannot create an event with attendee info (which is an EventKit limitation as mentioned here https://apple.co/3toRnDO)
  recurrenceRules?: RecurrenceRule[];
}

/**
 * EventAvailability values.
 */
export type EventAvailability = 'Busy' | 'Free' | 'Tentative';

/**
 * EventStatus values.
 */
export type EventStatus = 'Canceled' | 'Confirmed' | 'Tentative';

/**
 * Alarm interface.
 */
export interface Alarm {
  relativeOffsetSeconds: number;
}

/**
 * Participant interface.
 */
export interface Participant {
  name: string;
  email: string | null;
  role: ParticipantRole;
  status: ParticipantStatus;
}

/**
 * ParticipantRole values.
 */
export type ParticipantRole = 'Required' | 'Optional' | 'Unknown';

/**
 * ParticipantStatus values.
 */
export type ParticipantStatus = 'Accepted' | 'Declined' | 'Pending' | 'Tentative' | 'Unknown';

/**
 * The recurrence rule as defined by https://datatracker.ietf.org/doc/html/rfc5545#section-3.3.10.
 */
export interface RecurrenceRule {
  frequency: RecurrenceFrequency;
  interval: number;
  daysOfTheWeek?: RecurrenceDayOfWeek[];
  daysOfTheMonth?: number[];
  monthsOfTheYear?: number[];
  weeksOfTheYear?: number[];
  daysOfTheYear?: number[];
  setPositions?: number[];
  end?: RecurrenceEnd;
}

/**
 * RecurrenceFrequency values.
 */
export type RecurrenceFrequency = 'Daily' | 'Weekly' | 'Monthly' | 'Yearly';

/**
 * RecurrenceDayOfWeek interface.
 */
export interface RecurrenceDayOfWeek {
  dayOfTheWeek: Weekday;
  weekNumber: number;
}

/**
 * Weekday values.
 */
export type Weekday = 'Sunday' | 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday' | 'Saturday';

/**
 * RecurrenceEnd interface.
 */
export interface RecurrenceEnd {
  endDateSecondsUTC?: number;
  occurrenceCount?: number;
}

/**
 * CalendarServiceOptions interface.
 */
export interface CalendarServiceOptions {
  permissionRationaleText?: string;
  span?: Span;
}

/**
 * Span values.
 */
export type Span = 'ThisEvent' | 'ThisAndFollowingEvents';

/**
 * CalendarServiceFailure interface.
 */
export interface CalendarServiceFailure {
  code: CalendarServiceFailureCode;
  message: string;
}

/**
 * Possible failure codes.
 */
export type CalendarServiceFailureCode =
  | 'USER_DENIED_PERMISSION' // Permission was denied by user when prompt.
  | 'NOT_FOUND' // A specified item (calendar or event) was not found.
  | 'SERVICE_NOT_ENABLED' // The service is not enabled and therefore cannot be used.
  | 'UNKNOWN_REASON'; // An error happened in the native code that is not permission based. Will give more information in the CalendarServiceFailure message.
```
