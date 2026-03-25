/**
 * Invocable Apex for Flow/Process Builder integration
 *              Exposes business logic as a Flow Action
 *
 * FLOW USAGE:
 * 1. Add Action element in Flow Builder
 * 2. Search for "{{ActionLabel}}"
 * 3. Map input/output variables
 *
 * PATTERN: Request/Response wrappers enable complex data exchange
 *          with Flow while maintaining type safety
 */
public with sharing class {{ClassName}}Invocable {

    // ═══════════════════════════════════════════════════════════════════════
    // INVOCABLE METHOD
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Main entry point for Flow Actions
     *              Method must be static, accept List<Request>, return List<Response>
     *              This signature supports bulkification when Flow runs for multiple records
     *
     * @param requests List of request wrappers from Flow
     * @return List of response wrappers to Flow
     */
    @InvocableMethod(
        label='{{ActionLabel}}'
        description='{{ActionDescription}}'
        category='{{Category}}'
    )
    public static List<Response> execute(List<Request> requests) {
        List<Response> responses = new List<Response>();

        // ─────────────────────────────────────────────────────────────────
        // BULKIFICATION: Collect all IDs first, then query once
        // Avoids SOQL-in-loop governor limit issues
        // ─────────────────────────────────────────────────────────────────
        Set<Id> recordIds = new Set<Id>();
        for (Request req : requests) {
            if (req.recordId != null) {
                recordIds.add(req.recordId);
            }
        }

        // Single bulk query with USER_MODE for FLS/CRUD enforcement
        Map<Id, {{ObjectName}}> recordsById = new Map<Id, {{ObjectName}}>();
        if (!recordIds.isEmpty()) {
            recordsById = new Map<Id, {{ObjectName}}>(
                [SELECT Id, Name
                 FROM {{ObjectName}}
                 WHERE Id IN :recordIds
                 WITH USER_MODE]
            );
        }

        // ─────────────────────────────────────────────────────────────────
        // PROCESS EACH REQUEST
        // ─────────────────────────────────────────────────────────────────
        for (Request req : requests) {
            Response res = new Response();

            try {
                {{ObjectName}} record = recordsById.get(req.recordId);

                if (record == null) {
                    res.isSuccess = false;
                    res.errorMessage = 'Record not found: ' + req.recordId;
                } else {
                    // Delegate to business logic method
                    res = processRecord(record, req);
                }
            } catch (Exception e) {
                res.isSuccess = false;
                res.errorMessage = e.getMessage();
                res.errorType = e.getTypeName();
            }

            responses.add(res);
        }

        return responses;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // BUSINESS LOGIC
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Core business logic implementation
     *              Separated for testability and reuse
     *
     * @param record The record to process
     * @param req The original request with parameters
     * @return Response with results
     */
    private static Response processRecord({{ObjectName}} record, Request req) {
        Response res = new Response();

        // TODO: Implement your business logic here
        // Example: Calculate, validate, transform, etc.

        res.isSuccess = true;
        res.outputMessage = 'Successfully processed: ' + record.Name;
        res.outputRecordId = record.Id;

        return res;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // INVOCABLE VARIABLE WRAPPERS
    // Each variable becomes a Flow input/output parameter
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Request wrapper for Flow inputs
     *              Each @InvocableVariable appears in Flow's input mapping UI
     *
     * SUPPORTED TYPES:
     * - Primitives: Boolean, Date, DateTime, Decimal, Double, Integer, Long, String, Time
     * - SObject types: Account, Contact, etc.
     * - Collections: List<T> of above types
     * - Apex-defined types (nested classes with @InvocableVariable)
     */
    public class Request {
        @InvocableVariable(
            label='Record ID'
            description='ID of the record to process'
            required=true
        )
        public Id recordId;

        @InvocableVariable(
            label='Operation Type'
            description='Type of operation: validate, process, calculate'
            required=false
        )
        public String operationType;

        @InvocableVariable(
            label='Include Related Records'
            description='Whether to include related records in processing'
            required=false
        )
        public Boolean includeRelated;

        @InvocableVariable(
            label='Amount'
            description='Numeric amount for calculations'
            required=false
        )
        public Decimal amount;

        @InvocableVariable(
            label='Additional Record IDs'
            description='Collection of additional record IDs'
            required=false
        )
        public List<Id> additionalRecordIds;
    }

    /**
     * Response wrapper for Flow outputs
     *              Each @InvocableVariable appears in Flow's output mapping UI
     *
     * TIP: Always include isSuccess and errorMessage for consistent error handling
     */
    public class Response {
        @InvocableVariable(
            label='Is Success'
            description='Whether the operation completed successfully'
        )
        public Boolean isSuccess;

        @InvocableVariable(
            label='Error Message'
            description='Error message if operation failed (null if successful)'
        )
        public String errorMessage;

        @InvocableVariable(
            label='Error Type'
            description='Exception type name for debugging'
        )
        public String errorType;

        @InvocableVariable(
            label='Output Message'
            description='Human-readable result message'
        )
        public String outputMessage;

        @InvocableVariable(
            label='Output Record ID'
            description='ID of processed or created record'
        )
        public Id outputRecordId;

        @InvocableVariable(
            label='Output Value'
            description='Primary result value (string format)'
        )
        public String outputValue;

        @InvocableVariable(
            label='Output Amount'
            description='Numeric result (for calculations)'
        )
        public Decimal outputAmount;

        @InvocableVariable(
            label='Output Records'
            description='Collection of processed records'
        )
        public List<SObject> outputRecords;

        /**
         * Convenience constructor for success responses
         */
        public Response() {
            this.isSuccess = false;
        }

        /**
         * Factory method for success response
         */
        public static Response success(String message, Id recordId) {
            Response res = new Response();
            res.isSuccess = true;
            res.outputMessage = message;
            res.outputRecordId = recordId;
            return res;
        }

        /**
         * Factory method for error response
         */
        public static Response error(String message) {
            Response res = new Response();
            res.isSuccess = false;
            res.errorMessage = message;
            return res;
        }
    }
}
