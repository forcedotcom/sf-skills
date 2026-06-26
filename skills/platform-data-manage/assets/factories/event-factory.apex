/**
 * Test Data Factory for Event records
 * Supports bulk creation with polymorphic Who/What relationships and scheduling
 *
 * Usage:
 *   List<Event> events = TestDataFactory_Event.create(200);
 *   List<Event> eventsForContact = TestDataFactory_Event.createForWho(50, contactId);
 *   List<Event> allDayEvents = TestDataFactory_Event.createAllDay(50);
 */
public class TestDataFactory_Event {

    private static final String DEFAULT_SUBJECT_PREFIX = 'Test Event ';
    private static final Integer DEFAULT_DURATION_MINUTES = 60;

    /**
     * Create and insert Event records (creates related Contact automatically)
     * @param count Number of records to create
     * @return List of inserted Event records with IDs
     */
    public static List<Event> create(Integer count) {
        return create(count, true);
    }

    /**
     * Create Event records with insert option
     * @param count Number of records to create
     * @param doInsert Whether to insert records
     * @return List of Event records
     */
    public static List<Event> create(Integer count, Boolean doInsert) {
        // Create parent Account and Contact for Who field
        Account parentAccount = new Account(Name = 'Test Parent Account for Events');
        insert parentAccount;

        Contact parentContact = new Contact(
            FirstName = 'Test',
            LastName = 'EventContact',
            AccountId = parentAccount.Id
        );
        insert parentContact;

        List<Event> records = new List<Event>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, parentContact.Id, parentAccount.Id));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Event records for a specific Who (Contact or Lead)
     * @param count Number of records to create
     * @param whoId Contact or Lead ID for the Who field
     * @return List of inserted Event records
     */
    public static List<Event> createForWho(Integer count, Id whoId) {
        return createForWho(count, whoId, true);
    }

    /**
     * Create Event records for a specific Who with insert option
     * @param count Number of records to create
     * @param whoId Contact or Lead ID
     * @param doInsert Whether to insert records
     * @return List of Event records
     */
    public static List<Event> createForWho(Integer count, Id whoId, Boolean doInsert) {
        List<Event> records = new List<Event>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, whoId, null));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Event records for a specific What (Account, Opportunity, Case, etc.)
     * @param count Number of records to create
     * @param whatId Account, Opportunity, or Case ID
     * @return List of inserted Event records
     */
    public static List<Event> createForWhat(Integer count, Id whatId) {
        return createForWhat(count, whatId, true);
    }

    /**
     * Create Event records for a specific What with insert option
     * @param count Number of records to create
     * @param whatId Account, Opportunity, or Case ID
     * @param doInsert Whether to insert records
     * @return List of Event records
     */
    public static List<Event> createForWhat(Integer count, Id whatId, Boolean doInsert) {
        List<Event> records = new List<Event>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i, null, whatId));
        }
        if (doInsert && !records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create all-day Event records
     * @param count Number of records to create
     * @return List of inserted all-day Event records
     */
    public static List<Event> createAllDay(Integer count) {
        Account parentAccount = new Account(Name = 'Test Account for All-Day Events');
        insert parentAccount;

        List<Event> records = new List<Event>();
        for (Integer i = 0; i < count; i++) {
            Event e = new Event(
                Subject = 'All Day Event ' + String.valueOf(i).leftPad(5, '0'),
                WhatId = parentAccount.Id,
                IsAllDayEvent = true,
                ActivityDate = Date.today().addDays(i),
                Description = 'Test all-day event created by TestDataFactory'
            );
            records.add(e);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create recurring Event records
     * @param count Number of recurring event series to create
     * @param recurrencePattern Recurrence pattern (Daily, Weekly, Monthly)
     * @return List of inserted recurring Event records
     */
    public static List<Event> createRecurring(Integer count, String recurrencePattern) {
        Account parentAccount = new Account(Name = 'Test Account for Recurring Events');
        insert parentAccount;

        List<Event> records = new List<Event>();
        DateTime startTime = DateTime.now().addDays(1);

        for (Integer i = 0; i < count; i++) {
            Event e = new Event(
                Subject = 'Recurring Event ' + String.valueOf(i).leftPad(5, '0'),
                WhatId = parentAccount.Id,
                StartDateTime = startTime.addHours(i),
                EndDateTime = startTime.addHours(i + 1),
                IsRecurrence = true,
                RecurrenceType = recurrencePattern,
                RecurrenceInterval = 1,
                RecurrenceStartDateTime = startTime.addHours(i),
                RecurrenceEndDateOnly = Date.today().addMonths(3),
                Description = 'Test recurring event created by TestDataFactory'
            );
            records.add(e);
        }
        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Events with varied types for reporting testing
     * @param count Number of records to create
     * @return List of inserted Event records with varied types
     */
    public static List<Event> createWithVariedTypes(Integer count) {
        List<String> types = new List<String>{
            'Meeting', 'Call', 'Email', 'Other', 'Webinar',
            'Conference', 'Demo', 'Training', 'Interview', 'Presentation'
        };

        Account parentAccount = new Account(Name = 'Test Account for Varied Events');
        insert parentAccount;

        List<Event> records = new List<Event>();
        for (Integer i = 0; i < count; i++) {
            Event e = buildRecord(i, null, parentAccount.Id);
            e.Type = types[Math.mod(i, types.size())];
            records.add(e);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Create Events scheduled at different times for calendar testing
     * @param count Number of records to create
     * @param startDate First event date
     * @return List of inserted Event records spread across dates
     */
    public static List<Event> createSpreadAcrossDates(Integer count, Date startDate) {
        Account parentAccount = new Account(Name = 'Test Account for Calendar Events');
        insert parentAccount;

        List<Event> records = new List<Event>();
        DateTime baseDateTime = DateTime.newInstance(startDate, Time.newInstance(9, 0, 0, 0));

        for (Integer i = 0; i < count; i++) {
            Event e = new Event(
                Subject = 'Calendar Event ' + String.valueOf(i).leftPad(5, '0'),
                WhatId = parentAccount.Id,
                StartDateTime = baseDateTime.addDays(i),
                EndDateTime = baseDateTime.addDays(i).addHours(1),
                Description = 'Test calendar event created by TestDataFactory'
            );
            records.add(e);
        }

        if (!records.isEmpty()) {
            insert records;
        }
        return records;
    }

    /**
     * Build a single Event record with default values
     * @param index Record index for unique naming
     * @param whoId Contact or Lead ID (optional)
     * @param whatId Account, Opportunity, or Case ID (optional)
     * @return Event record (not inserted)
     */
    private static Event buildRecord(Integer index, Id whoId, Id whatId) {
        String indexStr = String.valueOf(index).leftPad(5, '0');
        DateTime startTime = DateTime.now().addDays(1).addHours(index);

        return new Event(
            Subject = DEFAULT_SUBJECT_PREFIX + indexStr,
            WhoId = whoId,
            WhatId = whatId,
            StartDateTime = startTime,
            EndDateTime = startTime.addMinutes(DEFAULT_DURATION_MINUTES),
            Location = 'Test Location ' + index,
            Description = 'Test event created by TestDataFactory for automated testing. Event index: ' + index,
            Type = 'Meeting',
            ShowAs = 'Busy',
            IsPrivate = false,
            IsReminderSet = false
        );
    }

    /**
     * Get IDs of created records for cleanup
     * @param records List of Event records
     * @return Set of Event IDs
     */
    public static Set<Id> getIds(List<Event> records) {
        Set<Id> ids = new Set<Id>();
        for (Event e : records) {
            if (e.Id != null) {
                ids.add(e.Id);
            }
        }
        return ids;
    }

    /**
     * Delete records by IDs (cleanup utility)
     * @param recordIds Set of Event IDs to delete
     */
    public static void cleanup(Set<Id> recordIds) {
        if (!recordIds.isEmpty()) {
            delete [SELECT Id FROM Event WHERE Id IN :recordIds];
        }
    }
}
