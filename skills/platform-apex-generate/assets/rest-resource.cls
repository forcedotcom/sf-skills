/**
 * REST API endpoint for {SObject} operations.
 *              Exposes CRUD operations via @RestResource at /services/apexrest/{urlPath}/v1/*.
 *              Uses versioned URL mapping for future-proof API evolution.
 *              All queries use WITH USER_MODE for CRUD/FLS enforcement.
 *
 * Authentication: OAuth 2.0 via Connected App
 * Base URL: /services/apexrest/{urlPath}/v1/
 */
@RestResource(urlMapping='/{urlPath}/v1/*')
global with sharing class {ClassName} {

    // ─── Constants ────────────────────────────────────────────────────────
    private static final Integer DEFAULT_PAGE_SIZE = 20;
    private static final Integer MAX_PAGE_SIZE = 200;
    private static final String ERROR_MISSING_ID = 'Record Id is required in the URL path.';
    private static final String ERROR_INVALID_ID = 'Invalid Salesforce Id format.';
    private static final String ERROR_MISSING_BODY = 'Request body is required.';
    private static final String ERROR_NOT_FOUND = '{SObject} record not found.';
    private static final String ERROR_INSUFFICIENT_ACCESS = 'Insufficient access to perform this operation.';

    // ─── GET — Retrieve ───────────────────────────────────────────────────

    /**
     * Retrieves a single {SObject} by Id (URL path) or a paginated list (query params).
     * Single: GET /services/apexrest/{urlPath}/v1/{recordId}
     * List:   GET /services/apexrest/{urlPath}/v1?pageSize=20&offset=0
     * @return ApiResponse containing the requested data
     */
    @HttpGet
    global static ApiResponse doGet() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;

        try {
            String recordId = extractIdFromUri(req.requestURI);

            if (String.isNotBlank(recordId)) {
                return getSingleRecord(recordId, res);
            }
            return getRecordList(req, res);

        } catch (Exception e) {
            return handleError(res, 500, e.getMessage());
        }
    }

    // ─── POST — Create ───────────────────────────────────────────────────

    /**
     * Creates a new {SObject} record from the JSON request body.
     * POST /services/apexrest/{urlPath}/v1/
     * @return ApiResponse with the created record Id
     */
    @HttpPost
    global static ApiResponse doPost() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;

        try {
            if (req.requestBody == null || String.isBlank(req.requestBody.toString())) {
                return handleError(res, 400, ERROR_MISSING_BODY);
            }

            {ClassName}Request payload = ({ClassName}Request) JSON.deserialize(
                req.requestBody.toString(),
                {ClassName}Request.class
            );

            // TODO: Map request payload to SObject fields
            {SObject} record = new {SObject}(
                Name = payload.name
            );

            Database.SaveResult saveResult = Database.insert(record, true);
            if (saveResult.isSuccess()) {
                res.statusCode = 201;
                return new ApiResponse(true, 'Record created successfully.', record.Id);
            }

            return handleError(res, 422, saveResult.getErrors()[0].getMessage());

        } catch (JSONException e) {
            return handleError(res, 400, 'Malformed JSON: ' + e.getMessage());
        } catch (DmlException e) {
            return handleError(res, 422, 'Validation failed: ' + e.getDmlMessage(0));
        } catch (Exception e) {
            return handleError(res, 500, e.getMessage());
        }
    }

    // ─── PATCH — Partial Update ───────────────────────────────────────────

    /**
     * Partially updates an existing {SObject} record.
     * PATCH /services/apexrest/{urlPath}/v1/{recordId}
     * @return ApiResponse confirming the update
     */
    @HttpPatch
    global static ApiResponse doPatch() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;

        try {
            String recordId = extractIdFromUri(req.requestURI);
            if (String.isBlank(recordId)) {
                return handleError(res, 400, ERROR_MISSING_ID);
            }
            if (!isValidSalesforceId(recordId)) {
                return handleError(res, 400, ERROR_INVALID_ID);
            }
            if (req.requestBody == null || String.isBlank(req.requestBody.toString())) {
                return handleError(res, 400, ERROR_MISSING_BODY);
            }

            List<{SObject}> existing = [
                SELECT Id FROM {SObject} WHERE Id = :recordId WITH USER_MODE LIMIT 1
            ];
            if (existing.isEmpty()) {
                return handleError(res, 404, ERROR_NOT_FOUND);
            }

            Map<String, Object> fieldUpdates = (Map<String, Object>) JSON.deserializeUntyped(
                req.requestBody.toString()
            );

            {SObject} record = existing[0];
            // TODO: Apply allowed field updates from the payload to the record
            // for (String fieldName : fieldUpdates.keySet()) {
            //     record.put(fieldName, fieldUpdates.get(fieldName));
            // }

            Database.SaveResult saveResult = Database.update(record, true);
            if (saveResult.isSuccess()) {
                res.statusCode = 200;
                return new ApiResponse(true, 'Record updated successfully.', record.Id);
            }

            return handleError(res, 422, saveResult.getErrors()[0].getMessage());

        } catch (JSONException e) {
            return handleError(res, 400, 'Malformed JSON: ' + e.getMessage());
        } catch (DmlException e) {
            return handleError(res, 422, 'Validation failed: ' + e.getDmlMessage(0));
        } catch (Exception e) {
            return handleError(res, 500, e.getMessage());
        }
    }

    // ─── DELETE — Remove ──────────────────────────────────────────────────

    /**
     * Deletes a {SObject} record by Id.
     * DELETE /services/apexrest/{urlPath}/v1/{recordId}
     * @return ApiResponse confirming the deletion
     */
    @HttpDelete
    global static ApiResponse doDelete() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;

        try {
            String recordId = extractIdFromUri(req.requestURI);
            if (String.isBlank(recordId)) {
                return handleError(res, 400, ERROR_MISSING_ID);
            }
            if (!isValidSalesforceId(recordId)) {
                return handleError(res, 400, ERROR_INVALID_ID);
            }

            List<{SObject}> existing = [
                SELECT Id FROM {SObject} WHERE Id = :recordId WITH USER_MODE LIMIT 1
            ];
            if (existing.isEmpty()) {
                return handleError(res, 404, ERROR_NOT_FOUND);
            }

            Database.DeleteResult deleteResult = Database.delete(existing[0], true);
            if (deleteResult.isSuccess()) {
                res.statusCode = 200;
                return new ApiResponse(true, 'Record deleted successfully.', recordId);
            }

            return handleError(res, 422, deleteResult.getErrors()[0].getMessage());

        } catch (DmlException e) {
            return handleError(res, 422, e.getDmlMessage(0));
        } catch (Exception e) {
            return handleError(res, 500, e.getMessage());
        }
    }

    // ─── Private Helpers ──────────────────────────────────────────────────

    private static ApiResponse getSingleRecord(String recordId, RestResponse res) {
        if (!isValidSalesforceId(recordId)) {
            return handleError(res, 400, ERROR_INVALID_ID);
        }

        List<{SObject}> records = [
            SELECT Id, Name, CreatedDate, LastModifiedDate
            FROM {SObject}
            WHERE Id = :recordId
            WITH USER_MODE
            LIMIT 1
        ];

        if (records.isEmpty()) {
            return handleError(res, 404, ERROR_NOT_FOUND);
        }

        res.statusCode = 200;
        ApiResponse response = new ApiResponse(true, 'Record retrieved successfully.', recordId);
        response.data = records[0];
        return response;
    }

    private static ApiResponse getRecordList(RestRequest req, RestResponse res) {
        Integer pageSize = getIntParam(req, 'pageSize', DEFAULT_PAGE_SIZE);
        Integer offset = getIntParam(req, 'offset', 0);

        pageSize = Math.min(pageSize, MAX_PAGE_SIZE);

        List<{SObject}> records = [
            SELECT Id, Name, CreatedDate, LastModifiedDate
            FROM {SObject}
            WITH USER_MODE
            ORDER BY Name ASC
            LIMIT :pageSize
            OFFSET :offset
        ];

        res.statusCode = 200;
        ApiResponse response = new ApiResponse(true, 'Records retrieved successfully.', null);
        response.records = records;
        response.pageSize = pageSize;
        response.offset = offset;
        return response;
    }

    private static String extractIdFromUri(String uri) {
        String lastSegment = uri.substringAfterLast('/');
        if (String.isBlank(lastSegment) || lastSegment == 'v1') {
            return null;
        }
        return lastSegment;
    }

    private static Boolean isValidSalesforceId(String idValue) {
        return Pattern.matches('[a-zA-Z0-9]{15,18}', idValue);
    }

    private static Integer getIntParam(RestRequest req, String paramName, Integer defaultValue) {
        String paramValue = req.params.get(paramName);
        if (String.isBlank(paramValue)) {
            return defaultValue;
        }
        try {
            return Integer.valueOf(paramValue);
        } catch (TypeException e) {
            return defaultValue;
        }
    }

    private static ApiResponse handleError(RestResponse res, Integer statusCode, String message) {
        res.statusCode = statusCode;
        return new ApiResponse(false, message, null);
    }

    // ─── Request / Response DTOs ──────────────────────────────────────────

    /**
     * Inbound request payload for POST operations.
     * Extend with additional fields as needed.
     */
    global class {ClassName}Request {
        global String name;
        // TODO: Add fields matching the expected JSON request body
    }

    /**
     * Standardized API response envelope.
     * All endpoints return this structure for consistent client parsing.
     */
    global class ApiResponse {
        global Boolean success;
        global String message;
        global String recordId;
        global SObject data;
        global List<SObject> records;
        global Integer pageSize;
        global Integer offset;

        global ApiResponse(Boolean success, String message, String recordId) {
            this.success = success;
            this.message = message;
            this.recordId = recordId;
        }
    }
}