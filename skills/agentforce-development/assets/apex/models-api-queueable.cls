/**
 * @description Queueable job for AI generation using Agentforce Models API
 *              Generates {{Description}} for {{ObjectName}} records
 * @author {{Author}}
 * @date {{Date}}
 *
 * @requires API v61.0+ (Spring '24)
 * @requires Einstein Generative AI enabled
 * @requires Einstein Generative AI User permission set
 *
 * @example
 * // Invoke from trigger or other context:
 * List<Id> recordIds = new List<Id>{ '001xx000003DGXXX' };
 * System.enqueueJob(new {{ClassName}}_AI_Queueable(recordIds));
 */
public with sharing class {{ClassName}}_AI_Queueable implements Queueable, Database.AllowsCallouts {

    // ═══════════════════════════════════════════════════════════════════════
    // CONFIGURATION
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * Available Models:
     * - sfdc_ai__DefaultOpenAIGPT4OmniMini  (Cost-effective, faster)
     * - sfdc_ai__DefaultOpenAIGPT4Omni      (More capable, slower)
     * - sfdc_ai__DefaultAnthropic           (Claude - nuanced)
     * - sfdc_ai__DefaultGoogleGemini        (Multimodal capable)
     */
    private static final String AI_MODEL = 'sfdc_ai__DefaultOpenAIGPT4OmniMini';

    /**
     * Maximum records to process in a single job.
     * Recommended: 10-20 for AI processing to avoid timeouts.
     */
    private static final Integer MAX_RECORDS_PER_JOB = 20;

    // ═══════════════════════════════════════════════════════════════════════
    // INSTANCE VARIABLES
    // ═══════════════════════════════════════════════════════════════════════

    private List<Id> recordIds;

    // ═══════════════════════════════════════════════════════════════════════
    // CONSTRUCTOR
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @description Constructor
     * @param recordIds List of {{ObjectName}} record IDs to process
     */
    public {{ClassName}}_AI_Queueable(List<Id> recordIds) {
        this.recordIds = recordIds;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // QUEUEABLE EXECUTION
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @description Execute the queueable job
     * @param context QueueableContext
     */
    public void execute(QueueableContext context) {
        if (recordIds == null || recordIds.isEmpty()) {
            return;
        }

        // Split into current batch and remaining
        List<Id> currentBatch = new List<Id>();
        List<Id> remainingIds = new List<Id>();

        for (Integer i = 0; i < recordIds.size(); i++) {
            if (i < MAX_RECORDS_PER_JOB) {
                currentBatch.add(recordIds[i]);
            } else {
                remainingIds.add(recordIds[i]);
            }
        }

        // Process current batch
        processRecords(currentBatch);

        // Chain next job if more records remain
        if (!remainingIds.isEmpty() && !Test.isRunningTest()) {
            System.enqueueJob(new {{ClassName}}_AI_Queueable(remainingIds));
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PROCESSING LOGIC
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @description Process a batch of records
     * @param batchIds Record IDs to process in this batch
     */
    private void processRecords(List<Id> batchIds) {
        // Query records with fields needed for AI prompt
        List<{{ObjectName}}> records = [
            SELECT Id, Name
                   // TODO: Add fields needed for AI context
                   // , Description, Subject, Type
            FROM {{ObjectName}}
            WHERE Id IN :batchIds
            WITH USER_MODE
        ];

        List<{{ObjectName}}> toUpdate = new List<{{ObjectName}}>();

        for ({{ObjectName}} record : records) {
            try {
                // Generate AI content
                String aiContent = generateAIContent(record);

                if (String.isNotBlank(aiContent)) {
                    // TODO: Update the target field with AI-generated content
                    // record.AI_Summary__c = aiContent;
                    toUpdate.add(record);
                }
            } catch (Exception e) {
                // Log error but continue processing other records
                logError(record.Id, e);
            }
        }

        // Batch update
        if (!toUpdate.isEmpty()) {
            try {
                update toUpdate;
            } catch (DmlException e) {
                System.debug(LoggingLevel.ERROR, 'DML Error: ' + e.getMessage());
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // AI GENERATION
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @description Generate AI content for a single record
     * @param record The record to generate content for
     * @return Generated text content
     */
    private String generateAIContent({{ObjectName}} record) {
        // Build the prompt with record context
        String prompt = buildPrompt(record);

        // Create Models API request
        aiplatform.ModelsAPI.createGenerations_Request request =
            new aiplatform.ModelsAPI.createGenerations_Request();
        request.modelName = AI_MODEL;

        aiplatform.ModelsAPI_GenerationRequest genRequest =
            new aiplatform.ModelsAPI_GenerationRequest();
        genRequest.prompt = prompt;
        request.body = genRequest;

        // Call the API
        aiplatform.ModelsAPI.createGenerations_Response response =
            aiplatform.ModelsAPI.createGenerations(request);

        // Extract and return generated text
        if (response.Code200 != null &&
            response.Code200.generations != null &&
            !response.Code200.generations.isEmpty()) {
            return response.Code200.generations[0].text;
        }

        return null;
    }

    /**
     * @description Build the AI prompt for a record
     * @param record The record to build prompt for
     * @return Formatted prompt string
     */
    private String buildPrompt({{ObjectName}} record) {
        // TODO: Customize this prompt for your use case
        String prompt =
            '{{PromptInstructions}}\n\n' +
            'Record Information:\n' +
            '- Name: ' + record.Name + '\n';
            // TODO: Add more fields as needed
            // '- Description: ' + record.Description + '\n' +
            // '- Type: ' + record.Type + '\n';

        return prompt;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // ERROR HANDLING
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @description Log processing errors
     * @param recordId The record that failed
     * @param e The exception that occurred
     */
    private void logError(Id recordId, Exception e) {
        System.debug(LoggingLevel.ERROR,
            '{{ClassName}}_AI_Queueable Error for ' + recordId + ': ' + e.getMessage());
        System.debug(LoggingLevel.ERROR, 'Stack Trace: ' + e.getStackTraceString());

        // TODO: Implement custom error logging
        // Options:
        // 1. Create Error_Log__c record
        // 2. Publish Platform Event for monitoring
        // 3. Send email notification
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TEST SUPPORT
    // ═══════════════════════════════════════════════════════════════════════

    /**
     * @description Test-visible method to verify prompt generation
     * @param record Test record
     * @return Generated prompt
     */
    @TestVisible
    private String testBuildPrompt({{ObjectName}} record) {
        return buildPrompt(record);
    }
}
