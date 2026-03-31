/**
 * Invocable Apex action for {describe the action}.
 * Callable from Flows, Process Builder, and Agentforce.
 * Accepts bulkified List<Request>, returns List<Response>.
 */
public with sharing class {ClassName} {

    // ─── Invocable Method ────────────────────────────────────────────────

    /**
     * {Describe what this action does}
     * @param requests List of Request inputs from the calling Flow
     * @return List of Response outputs returned to the calling Flow
     */
    @InvocableMethod(
        label='{Display Name}'
        description='{Describe the action for Flow Builder}'
        category='{Category}'
    )
    public static List<Response> execute(List<Request> requests) {
        List<Response> responses = new List<Response>();

        // Collect all Ids upfront for bulkified query
        Set<Id> allRecordIds = new Set<Id>();
        for (Request req : requests) {
            if (req.recordId != null) {
                allRecordIds.add(req.recordId);
            }
        }

        // Single bulkified query outside the loop
        Map<Id, {SObject}> recordMap = allRecordIds.isEmpty()
            ? new Map<Id, {SObject}>()
            : new Map<Id, {SObject}>([
                SELECT Id, Name
                // TODO: Add required fields
                FROM {SObject}
                WHERE Id IN :allRecordIds
                WITH USER_MODE
            ]);

        // Process each request
        for (Request req : requests) {
            responses.add(processRequest(req, recordMap));
        }

        return responses;
    }

    // ─── Private Helpers ─────────────────────────────────────────────────

    /**
     * Processes a single request and returns a response.
     * Errors are captured in the response, not thrown.
     * @param req The input request
     * @param recordMap Pre-queried records keyed by Id
     * @return A Response with success/error information
     */
    private static Response processRequest(Request req, Map<Id, {SObject}> recordMap) {
        Response res = new Response();

        try {
            {SObject} record = recordMap.get(req.recordId);
            if (record == null) {
                res.isSuccess = false;
                res.errorMessage = 'Record not found: ' + req.recordId;
                res.errorType = 'NOT_FOUND';
                return res;
            }

            // TODO: Implement business logic

            res.isSuccess = true;
        } catch (Exception e) {
            res.isSuccess = false;
            res.errorMessage = e.getMessage();
            res.errorType = e.getTypeName();
        }

        return res;
    }

    // ─── Request / Response DTOs ─────────────────────────────────────────

    /**
     * Input parameters from the calling Flow
     */
    public class Request {
        @InvocableVariable(label='Record Id' description='The Id of the record to process' required=true)
        public Id recordId;

        // TODO: Add additional input variables
        // @InvocableVariable(label='Field Value' description='Value to set' required=false)
        // public String fieldValue;
    }

    /**
     * Output results returned to the calling Flow
     */
    public class Response {
        @InvocableVariable(label='Success' description='Whether the action succeeded')
        public Boolean isSuccess;

        @InvocableVariable(label='Error Message' description='Error details if the action failed')
        public String errorMessage;

        @InvocableVariable(label='Error Type' description='Exception type name if the action failed')
        public String errorType;

        // TODO: Add additional output variables
        // @InvocableVariable(label='Result Id' description='Id of the created/updated record')
        // public Id resultId;
    }
}
