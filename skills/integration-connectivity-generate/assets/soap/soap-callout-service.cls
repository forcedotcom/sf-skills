/**
 * @description SOAP Web Service Callout Service
 *
 * Use Case: Integrations with SOAP/XML-based web services
 * - Legacy enterprise systems
 * - Government APIs
 * - Financial services (often SOAP-based)
 *
 * Prerequisites:
 * 1. Generate Apex from WSDL (Setup → Apex Classes → Generate from WSDL)
 * 2. Configure Named Credential or Remote Site Setting for endpoint
 *
 * This template wraps WSDL-generated stub classes with:
 * - Error handling
 * - Timeout configuration
 * - Logging
 *
 * @author {{Author}}
 * @date {{Date}}
 */
public with sharing class {{ServiceName}}SoapService {

    // Named Credential for SOAP endpoint (recommended over Remote Site Setting)
    private static final String NAMED_CREDENTIAL = 'callout:{{NamedCredentialName}}';

    // Timeout in milliseconds (max 120000)
    private static final Integer TIMEOUT_MS = 120000;

    /**
     * @description Call SOAP operation with request object
     *
     * Replace {{WsdlStubClass}} with your WSDL-generated class name
     * Replace {{PortType}} with the port/binding type from WSDL
     * Replace {{OperationName}} with the SOAP operation to call
     *
     * @param request Request object (WSDL-generated type)
     * @return Response object (WSDL-generated type)
     * @throws SoapCalloutException on errors
     */
    public static {{ResponseType}} callService({{RequestType}} request) {
        try {
            // Instantiate the WSDL-generated stub
            {{WsdlStubClass}}.{{PortType}} stub = new {{WsdlStubClass}}.{{PortType}}();

            // Configure endpoint
            // Option 1: Use Named Credential (recommended)
            stub.endpoint_x = NAMED_CREDENTIAL;

            // Option 2: Direct endpoint (requires Remote Site Setting)
            // stub.endpoint_x = '{{SoapEndpoint}}';

            // Set timeout
            stub.timeout_x = TIMEOUT_MS;

            // Set custom SOAP headers if needed
            // stub.inputHttpHeaders_x = new Map<String, String>{
            //     'X-Custom-Header' => 'value'
            // };

            // Make the SOAP call
            {{ResponseType}} response = stub.{{OperationName}}(request);

            // Log success
            System.debug(LoggingLevel.DEBUG, 'SOAP call successful: {{OperationName}}');

            return response;

        } catch (CalloutException e) {
            // Network/timeout error
            System.debug(LoggingLevel.ERROR, 'SOAP CalloutException: ' + e.getMessage());
            throw new SoapCalloutException('Connection error: ' + e.getMessage(), e);

        } catch (Exception e) {
            // SOAP fault or other error
            System.debug(LoggingLevel.ERROR, 'SOAP Error: ' + e.getMessage());
            System.debug(LoggingLevel.ERROR, 'Stack: ' + e.getStackTraceString());
            throw new SoapCalloutException('SOAP service error: ' + e.getMessage(), e);
        }
    }

    /**
     * @description Async SOAP call via Queueable
     *              Use this when calling from DML context (triggers)
     * @param request Request object
     * @param callbackId Optional ID for tracking the async job
     */
    public static void callServiceAsync({{RequestType}} request, Id callbackId) {
        System.enqueueJob(new SoapCalloutQueueable(request, callbackId));
    }

    /**
     * @description Queueable implementation for async SOAP calls
     */
    public class SoapCalloutQueueable implements Queueable, Database.AllowsCallouts {
        private {{RequestType}} request;
        private Id callbackId;

        public SoapCalloutQueueable({{RequestType}} request, Id callbackId) {
            this.request = request;
            this.callbackId = callbackId;
        }

        public void execute(QueueableContext context) {
            try {
                {{ResponseType}} response = callService(request);

                // Process response and update Salesforce record if needed
                if (callbackId != null) {
                    processCallback(response, callbackId);
                }

            } catch (Exception e) {
                System.debug(LoggingLevel.ERROR, 'Async SOAP call failed: ' + e.getMessage());
                // Consider: create error log, send notification
            }
        }
    }

    /**
     * @description Process async callback result
     * @param response SOAP response
     * @param callbackId Record ID to update with result
     */
    private static void processCallback({{ResponseType}} response, Id callbackId) {
        // TODO: Implement callback processing
        // Example: Update a record with the response data
        /*
        SObject record = callbackId.getSObjectType().newSObject(callbackId);
        record.put('Integration_Status__c', 'Complete');
        record.put('Integration_Response__c', JSON.serialize(response));
        update record;
        */
    }

    /**
     * @description Custom exception for SOAP callout errors
     */
    public class SoapCalloutException extends Exception {}
}

/*
 * ============================================================================
 * WSDL2APEX GENERATION GUIDE
 * ============================================================================
 *
 * Step 1: Obtain WSDL
 * -------------------
 * Get the WSDL file from the external system. It should be an XML file
 * defining the service, operations, and data types.
 *
 * Step 2: Generate Apex Classes
 * -----------------------------
 * 1. Go to Setup → Apex Classes
 * 2. Click "Generate from WSDL"
 * 3. Upload the WSDL file
 * 4. Choose a namespace (or accept default)
 * 5. Click "Generate Apex code"
 *
 * Step 3: Review Generated Classes
 * --------------------------------
 * Salesforce generates:
 * - Stub class ({{WsdlStubClass}}) with methods for each operation
 * - Request/Response wrapper classes
 * - Data type classes matching WSDL schema
 *
 * Step 4: Configure Access
 * ------------------------
 * Option A: Named Credential (Recommended)
 * - Create Named Credential with SOAP endpoint
 * - Set stub.endpoint_x = 'callout:NamedCredentialName'
 *
 * Option B: Remote Site Setting
 * - Create Remote Site Setting with SOAP endpoint domain
 * - Set stub.endpoint_x to full URL
 *
 * Step 5: Test the Integration
 * ----------------------------
 * Execute anonymous Apex:
 *
 * {{RequestType}} req = new {{RequestType}}();
 * req.field1 = 'value';
 * {{ResponseType}} resp = {{ServiceName}}SoapService.callService(req);
 * System.debug(resp);
 *
 * ============================================================================
 */
