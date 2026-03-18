/**
 * Invocable Apex template for Agent Script action backing logic.
 *
 * Wire this class to an Agent Script action with:
 *     target: "apex://{{ClassName}}"
 *
 * The @InvocableVariable field names on Request and Result become the
 * action's input and output names in the .agent file. They must match
 * character-for-character — including case.
 *
 * STUB USAGE: To create a minimal stub for unblocking deployment,
 * delete the business logic in execute() and return hardcoded values.
 * Do not add mock data, conditional logic, or JSON serialization to
 * stubs — keep them minimal.
 *
 * Replace all {{placeholders}} before use.
 */
public with sharing class {{ClassName}} {

    // ─── INVOCABLE METHOD ────────────────────────────────────────────
    //
    // Must be: static, accept List<Request>, return List<Result>.
    // This signature supports bulkification when the action is called
    // for multiple records in a single transaction.

    @InvocableMethod(
        label='{{ActionLabel}}'
        description='{{ActionDescription}}'
    )
    public static List<Result> execute(List<Request> requests) {
        List<Result> results = new List<Result>();

        // ── Bulkification: collect IDs first, query once ──
        // Avoids SOQL-in-loop governor limit issues.
        Set<Id> recordIds = new Set<Id>();
        for (Request req : requests) {
            if (req.recordId != null) {
                recordIds.add(req.recordId);
            }
        }

        // ── USER_MODE ──
        // `USER_MODE` enforces the running user's FLS/CRUD permissions.
        // For service agents, the running user is the Einstein Agent User.
        // If the user lacks read access to queried objects, queries return
        // 0 rows with NO error — a silent failure. Verify object permissions
        // before relying on `USER_MODE` queries.

        // Static SOQL (Preferred): Use `WITH USER_MODE` clause:
        Map<Id, {{SObjectName}}> recordsById = new Map<Id, {{SObjectName}}>();
        if (!recordIds.isEmpty()) {
            recordsById = new Map<Id, {{SObjectName}}>(
                [SELECT Id, Name
                 FROM {{SObjectName}}
                 WHERE Id IN :recordIds
                 WITH USER_MODE]
            );
        }

        // Dynamic SOQL (Optional): Use `AccessLevel.USER_MODE` parameter. DO NOT use `WITH USER_MODE` clause!
        // WARNING! `WITH USER_MODE` inside a dynamic string causes:
        //   System.QueryException: unexpected token: 'WITH'
        //
        // WRONG:
        //   String q = 'SELECT Id, Name FROM {{SObjectName}} WHERE Id IN :recordIds WITH USER_MODE';
        //   recordsById = new Map<Id, {{SObjectName}}>(Database.query(q));
        //
        // RIGHT:
        //   String q = 'SELECT Id, Name FROM {{SObjectName}} WHERE Id IN :recordIds';
        //   recordsById = new Map<Id, {{SObjectName}}>(Database.query(q, AccessLevel.USER_MODE));

        // ── Process each request ──
        for (Request req : requests) {
            Result r = new Result();
            try {
                {{SObjectName}} record = recordsById.get(req.recordId);
                if (record == null) {
                    r = errorResult('Record not found: ' + req.recordId);
                } else {
                    // TODO: Replace with actual business logic
                    r.isSuccess = true;
                    r.outputMessage = 'Processed: ' + record.Name;
                    r.outputRecordId = record.Id;
                }
            } catch (Exception e) {
                r = errorResult(e.getMessage());
            }
            results.add(r);
        }

        return results;
    }

    // ─── REQUEST WRAPPER ─────────────────────────────────────────────
    //
    // Each @InvocableVariable becomes an action input in Agent Script.
    // The field name here must exactly match the input name in the
    // .agent file's action definition.
    //
    // Supported types: Boolean, Date, DateTime, Decimal, Double,
    //   Integer, Long, String, Id, Time, SObject types, List<T>

    public class Request {
        @InvocableVariable(
            label='Record ID'
            description='ID of the record to process'
            required=true
        )
        public Id recordId;

        @InvocableVariable(
            label='Operation Type'
            description='Type of operation to perform'
            required=false
        )
        public String operationType;

        @InvocableVariable(
            label='Amount'
            description='Numeric amount for calculations'
            required=false
        )
        public Decimal amount;
    }

    // ─── RESULT WRAPPER ──────────────────────────────────────────────
    //
    // Each @InvocableVariable becomes an action output in Agent Script.
    // The field name here must exactly match the output name in the
    // .agent file's action definition.
    //
    // Always include isSuccess and errorMessage for consistent error
    // handling. The agent can check isSuccess to decide what to tell
    // the user.

    public class Result {
        @InvocableVariable(
            label='Is Success'
            description='Whether the operation completed successfully'
        )
        public Boolean isSuccess;

        @InvocableVariable(
            label='Error Message'
            description='Error message if operation failed'
        )
        public String errorMessage;

        @InvocableVariable(
            label='Output Message'
            description='Human-readable result for the agent to relay'
        )
        public String outputMessage;

        @InvocableVariable(
            label='Output Record ID'
            description='ID of the processed or created record'
        )
        public Id outputRecordId;

        @InvocableVariable(
            label='Output Value'
            description='Primary result value'
        )
        public String outputValue;

        @InvocableVariable(
            label='Output Amount'
            description='Numeric result for calculations'
        )
        public Decimal outputAmount;

    }

    // ── Error factory ──────────────────────────────────────────────────
    //
    // Centralizes error construction so every failure path sets both
    // isSuccess = false and errorMessage consistently. Defined on the
    // outer class because Apex prohibits static methods in inner classes.

    private static Result errorResult(String message) {
        Result r = new Result();
        r.isSuccess = false;
        r.errorMessage = message;
        return r;
    }
}
