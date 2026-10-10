---
name: generate-doc-description
description: Call use_skill as your FIRST and ONLY action when the user asks to document, add descriptions to, annotate, or add doc:description attributes to Mule XML files, flows, components, or connectors. Do not read project files first — this skill provides instructions for when to read files. Covers documenting all Mule elements in src/main/mule including flows, sub-flows, configs, listeners, processors, transforms, error handlers, and connectors. When you call use_skill, it must be the only tool call in that response.
metadata:
  author: mule-dx-tooling
  version: "1.0.0"
---

## Overview

You are an XML documentation expert for MuleSoft. Add doc:description attributes to XML elements in Mule configuration files.

Scan the Mule project for configuration XML files in `src/main/mule/` and add or update `doc:description` attributes on elements that are missing them or have inaccurate descriptions.

## Rules
- **doc:description**: A meaningful 1-2 sentence purpose description. MUST NOT exceed 150 characters.
- Preserve ALL existing XML structure, attributes, CDATA blocks, and content exactly as-is
- Do NOT modify, add, or remove any non-doc attributes or elements
- Do NOT modify existing doc:name attributes
- Ensure xmlns:doc="http://www.mulesoft.org/schema/mule/documentation" is present on the root element
- **CRITICAL: NEVER call Read and Write in the same turn** - When you call Read tool, do NOT call Write tool in that same response. Read in one turn, analyze and prepare changes, then Write in the next turn. This is a hard requirement - Read and Write are always separate turns.

## Important Rules
  - **Complete each file fully in ONE Write operation** - do NOT make edits in batches
  - **Do NOT modify doc:name attributes** - only work with doc:description
  - **Do NOT modify, add, or remove any non-doc attributes or elements**
  - **Preserve ALL existing XML structure, attributes, CDATA blocks, and content exactly as-is**
  - **Add doc:description to ALL elements listed in section B** - including loggers, processors, connectors, configs, etc.
  - **Do NOT change existing accurate descriptions** - only update if they're vague or incorrect
  - **Maintain XML formatting** - preserve indentation and structure
  - **Be specific** - avoid generic phrases like "processes data" or "handles request"
  - **Enforce 150 character limit** - all descriptions must be 150 characters or less

## Error Handling
  - If a file cannot be read, skip it and report the error
  - If XML parsing seems problematic, inform the user
  - If uncertain about a component's purpose, generate a conservative description or ask the user

## Step 1: Verify Project Structure
  - Check that `src/main/mule` directory exists in the current working directory
  - If not found, inform the user this doesn't appear to be a Mule application project

## Step 2: Find All Mule XML Files
  - Use Glob to find all XML files: `src/main/mule/**/*.xml`
  - If no files are found, inform the user and exit

## Step 3: Process Each File Completely
For each XML file found:

#### A. Read the entire file FIRST
**CRITICAL: You MUST read the actual file content before making any changes.**
**CRITICAL: When you call Read tool, do NOT call Write tool in the same turn. Read only.**
- Use Read tool to load the complete file contents
- Do NOT make assumptions about what's in the file
- Do NOT use content from other files as a template
- Examine the actual namespace declarations, element names, attribute order, and structure
- Verify the file structure matches expectations before proceeding
- After reading, proceed to step B in this same turn (analysis), but save Write for a later turn

#### B. Analyze and explicitly list all flows/components
**IMPORTANT: Before making ANY changes, explicitly list out what you found to prove you read the file:**

1. Search through the file and count all major components:
   - Count all `<flow>` elements and list each by name attribute
   - Count all `<sub-flow>` elements and list each by name attribute
   - Count all `<batch:job>` elements and list each by jobName attribute
   - Count global configs (`<*:config>`, `<*:listener-config>`, `<configuration-properties>`)
   - Count global error handlers (`<error-handler>` at top level, outside flows)

2. Output this analysis in a clear summary format:

   ```text
   Analyzing file: [filename]
   File size: [line count] lines

   Found:
   - [X] flows: [flow-name-1], [flow-name-2], [flow-name-3]...
   - [X] sub-flows: [subflow-name-1], [subflow-name-2]...
   - [X] batch jobs: [batch-job-name-1]...
   - [X] global configs
   - [X] global error handlers

   Proceeding to add doc:descriptions...
   ```

3. Then immediately proceed to step C (no user confirmation needed)

#### C. Identify elements that need documentation
Identify all elements that need documentation:

**Mule Flow Elements:**
- `<flow>`, `<sub-flow>` - Main entry points and business processes
- Source elements: `<http:listener>`, `<salesforce:*-listener>`, `<scheduler>`, etc.
- Processors: `<logger>`, `<set-variable>`, `<set-payload>`, `<remove-variable>`
- Routers: `<choice>`, `<when>`, `<otherwise>`, `<scatter-gather>`, `<foreach>`, `<until-successful>`
- Transforms: `<ee:transform>`, `<ee:message>`, `<ee:set-payload>`, `<ee:set-variable>`
- References: `<flow-ref>`
- Error handling: `<error-handler>`, `<on-error-propagate>`, `<on-error-continue>`
- Connector operations: `<*:create>`, `<*:query>`, `<*:request>`, etc.
- Global connector configs (if present): `<*:config>`, `<*:sfdc-config>`, `<*:listener-config>`
- Connection elements: `<*:basic-connection>`, `<*:token-based-authentication-connection>`
- `<configuration-properties>`
- Validators: `<validation:*>`
- Batch: `<batch:job>`, `<batch:step>`, etc.

**Connector Config Elements:**
- Config elements: `<*:config>`, `<*:sfdc-config>`, `<*:listener-config>`
- Connection sub-elements: `<*:basic-connection>`, `<*:token-based-authentication-connection>`, `<*:oauth-*-connection>`
- `<configuration-properties>`
- `<http:listener-connection>`, `<http:request-connection>`

**MUnit Test Elements:**
- `<munit:suite>` (root)
- `<munit:test>`
- Sections: `<munit:behavior>`, `<munit:execution>`, `<munit:validation>`
- Setup: `<munit:set-event>`, `<munit:set-attributes>`
- Assertions: `<munit-tools:assert-that>`, `<munit-tools:assert-equals>`
- Mocking: `<munit-tools:mock-when>`, `<munit-tools:then-return>`
- Verification: `<munit-tools:verify-call>`
- Flow references and processors within tests

For each element, determine if it needs a doc:description:
- **Add** if the element has no `doc:description` attribute
- **Update** if the existing `doc:description` is vague, generic, or doesn't accurately describe what the element does
- **Skip** if the `doc:description` already exists and accurately describes the element

#### C. Generate brief descriptions
Create descriptions that are:
- **Maximum 150 characters** - This is a hard limit
- **1-2 sentences** - Brief but meaningful
- **Specific** - Mention what it actually does, not just generic text
- **Present tense** - "Retrieves data" not "Retrieving data"
- **Business-focused** - What, not how
- **Scannable** - Easy to skim when reading through code

**Use the example template below** for guidance on how to write doc:description attributes for various Mule elements:

```xml
<?xml version="1.0" encoding="UTF-8"?>

<mule xmlns="http://www.mulesoft.org/schema/mule/core"
      xmlns:salesforce="http://www.mulesoft.org/schema/mule/salesforce"
      xmlns:netsuite="http://www.mulesoft.org/schema/mule/netsuite"
      xmlns:ee="http://www.mulesoft.org/schema/mule/ee/core"
      xmlns:doc="http://www.mulesoft.org/schema/mule/documentation"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:schemaLocation="
      http://www.mulesoft.org/schema/mule/core http://www.mulesoft.org/schema/mule/core/current/mule.xsd
      http://www.mulesoft.org/schema/mule/salesforce http://www.mulesoft.org/schema/mule/salesforce/current/mule-salesforce.xsd
      http://www.mulesoft.org/schema/mule/netsuite http://www.mulesoft.org/schema/mule/netsuite/current/mule-netsuite.xsd
      http://www.mulesoft.org/schema/mule/ee/core http://www.mulesoft.org/schema/mule/ee/core/current/mule-ee.xsd">

    <!-- Configuration Properties -->
    <configuration-properties file="config.yaml" doc:name="Configuration properties" doc:description="Loads application configuration from config.yaml file" />

    <!-- Salesforce Configuration -->
    <salesforce:sfdc-config name="salesforceConfig" doc:name="Salesforce Config" doc:description="Configures connection to Salesforce using basic authentication">
        <salesforce:basic-connection
                username="${salesforce.username}"
                password="${salesforce.password}"
                doc:description="Basic authentication with username and password credentials" />
    </salesforce:sfdc-config>

    <!-- NetSuite Configuration -->
    <netsuite:config name="netsuiteConfig" doc:name="NetSuite Config" doc:description="Configures connection to NetSuite using token-based authentication">
        <netsuite:token-based-authentication-connection
                consumerKey="${netsuite.consumerKey}"
                consumerSecret="${netsuite.consumerSecret}"
                tokenId="${netsuite.tokenId}"
                tokenSecret="${netsuite.tokenSecret}"
                account="${netsuite.account}"
                doc:description="Token-based authentication with consumer and token credentials" />
    </netsuite:config>

    <!-- Main Integration Flow -->
    <flow name="salesforce-to-netsuite-order-flow" doc:name="Salesforce to NetSuite Order Flow" doc:description="Syncs Closed Won Salesforce opportunities to NetSuite as sales orders">

        <!-- Salesforce Opportunity Listener -->
        <salesforce:modified-object-listener
                objectType="Opportunity"
                config-ref="salesforceConfig"
                doc:name="Listen for Modified Opportunities"
                doc:description="Polls Salesforce every 60 seconds for modified Opportunity records">
            <scheduling-strategy doc:description="Defines polling frequency for the listener">
                <fixed-frequency frequency="60000" doc:description="Polls every 60,000 milliseconds (1 minute)" />
            </scheduling-strategy>
        </salesforce:modified-object-listener>

        <logger level="INFO" message="Opportunity modified: #[payload.Id] - Stage: #[payload.StageName]" doc:name="Log Opportunity Update" doc:description="Logs the ID and stage of the modified Opportunity record" />

        <!-- Filter for Closed Won Opportunities -->
        <choice doc:name="Check if Closed Won" doc:description="Routes the flow based on whether the Opportunity is Closed Won">
            <when expression="#[payload.StageName == 'Closed Won']" doc:description="Processes opportunities with StageName equal to 'Closed Won'">

                <logger level="INFO" message="Processing Closed Won Opportunity: #[payload.Name] (Amount: #[payload.Amount])" doc:name="Log Closed Won" doc:description="Logs the name and amount of the Closed Won Opportunity being processed" />

                <!-- Transform Salesforce Opportunity to NetSuite Order -->
                <ee:transform doc:name="Map Opportunity to NetSuite Order" doc:description="Transforms Salesforce Opportunity data into NetSuite sales order format using DataWeave">
                    <ee:message doc:description="Defines the message transformation for the payload">
                        <ee:set-payload doc:description="Maps Opportunity fields to NetSuite order structure with customer and line items"><![CDATA[%dw 2.0
                            output application/java
                            ---
                            {
                            entity: "salesOrder",
                            entity @ {
                            customer: {
                            internalId: payload.AccountId default ""
                            }
                            },
                            tranId: payload.Id,
                            memo: "Order created from Salesforce Opportunity: " ++ payload.Name,
                            itemList: {
                            item: [{
                            item: {
                            internalId: "1"
                            },
                            quantity: 1,
                            rate: payload.Amount default 0
                            }]
                            }
                            }]]></ee:set-payload>
                    </ee:message>
                </ee:transform>

                <logger level="INFO" message="Transformed payload for NetSuite: #[output application/json --- payload]" doc:name="Log Transformed Payload" doc:description="Logs the transformed payload in JSON format for debugging" />

                <!-- Create Order in NetSuite -->
                <netsuite:add config-ref="netsuiteConfig" doc:name="Create NetSuite Order" doc:description="Creates a new sales order record in NetSuite using the add operation" />

                <logger level="INFO" message="NetSuite Order created successfully: #[payload]" doc:name="Log Success" doc:description="Logs successful creation of NetSuite order with response payload" />

            </when>
            <otherwise doc:description="Handles opportunities that are not in Closed Won stage">
                <logger level="INFO" message="Opportunity not in Closed Won stage, skipping. Current stage: #[payload.StageName]" doc:name="Log Skipped" doc:description="Logs that the Opportunity is being skipped with its current stage" />
            </otherwise>
        </choice>

        <!-- Error Handling -->
        <error-handler doc:description="Handles errors that occur during the flow execution">
            <on-error-propagate type="ANY" doc:description="Catches all error types and propagates them after logging">
                <logger level="ERROR" message="Error processing Opportunity: #[error.description]" doc:name="Log Error" doc:description="Logs error details when Opportunity processing fails" />
            </on-error-propagate>
        </error-handler>

    </flow>

</mule>
```

Study the template above to understand the level of detail and style expected for each element type. Note how descriptions are:
- Configuration properties and connector configs: mention what system and auth method
- Connection elements: specify auth type and credential types
- Flows and listeners: describe business process and what triggers them
- Scheduling strategies: state polling frequency in clear terms
- Loggers: explain what specific information is logged and why
- Choice routers and when/otherwise: describe conditions and routing logic
- Transforms: indicate source data, target format, and transformation purpose
- Connector operations: state what operation and which system
- Error handlers: explain what errors are caught and what action is taken

#### D. Make ALL edits to the file in ONE Write operation
**CRITICAL: Use ONE Write tool call per file, regardless of file size.**

- Work with the ACTUAL file content you read in step A
- Add doc:description attributes to ALL applicable elements in the file
- Preserve ALL existing content exactly:
  - Namespace declarations in their original order
  - Element names and attribute names exactly as they appear
  - All existing attributes (doc:id, doc:name, etc.)
  - CDATA blocks, comments, whitespace, and indentation
  - Line breaks and formatting

**Single Write Strategy:**
- Build the complete modified file content with ALL doc:description additions
- Use ONE Write tool call to save the complete modified file back to disk
- This ensures ONE approval prompt per file, regardless of file size
- No batching, no multiple writes - just one complete operation

**Why this single Write approach:**
- Simplest strategy - one write per file
- ONE approval prompt per file regardless of size
- Complete atomic operation - either all changes apply or none
- Easier to review all changes at once
- No risk of partial updates

## Step 4: Present Changes for Approval
After completing ALL edits for a file:
- Summarize what doc:description attributes were added (count by element type)
- Highlight any elements that were skipped and why
- The Write tool will prompt for user approval automatically
- If approved, move to the next file
- If denied, ask what needs adjustment and re-read the file to verify current state

## Step 5: Repeat for All Files
Continue this process for each XML file in the `src/main/mule/` directory.

## Step 6: Final Summary
After all files are processed, provide:
- Number of files scanned
- Number of files modified
- Total number of doc:description attributes added
- Total number of doc:description attributes updated
