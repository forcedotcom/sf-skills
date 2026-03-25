/**
 * Service class for {SObject} business logic.
 *              Follows separation of concerns: delegates queries to {SObject}Selector
 *              and SObject manipulation to {SObject}Domain where applicable.
 */
public with sharing class {SObject}Service {

    // ─── Constants ───────────────────────────────────────────────────────
    private static final String ERROR_NULL_INPUT = 'Input cannot be null or empty.';

    // ─── Public API ──────────────────────────────────────────────────────

    /**
     * {Describe the primary operation}
     * @param recordIds Set of {SObject} Ids to process
     * @return List of processed {SObject} records
     * @throws {SObject}ServiceException if processing fails
     * @example
     * Set<Id> ids = new Set<Id>{ someAccountId };
     * List<{SObject}> results = {SObject}Service.process{SObject}s(ids);
     */
    public static List<{SObject}> process{SObject}s(Set<Id> recordIds) {
        // Guard clause
        if (recordIds == null || recordIds.isEmpty()) {
            throw new {SObject}ServiceException(ERROR_NULL_INPUT);
        }

        // Query via Selector
        List<{SObject}> records = {SObject}Selector.selectByIds(recordIds);

        // Apply business logic
        // TODO: Implement business logic here

        // DML
        try {
            update records;
        } catch (DmlException e) {
            throw new {SObject}ServiceException(
                'Failed to update {SObject} records: ' + e.getMessage(), e
            );
        }

        return records;
    }

    // ─── Convenience Overloads ───────────────────────────────────────────

    /**
     * Single-record convenience overload
     * @param recordId The {SObject} Id to process
     * @return The processed {SObject} record
     */
    public static {SObject} process{SObject}(Id recordId) {
        List<{SObject}> results = process{SObject}s(new Set<Id>{ recordId });
        return results.isEmpty() ? null : results[0];
    }

    // ─── Private Helpers ─────────────────────────────────────────────────

    // TODO: Add private helper methods as needed

    // ─── Exception ───────────────────────────────────────────────────────

    /**
     * Custom exception for {SObject}Service errors
     */
    public class {SObject}ServiceException extends Exception {}
}
