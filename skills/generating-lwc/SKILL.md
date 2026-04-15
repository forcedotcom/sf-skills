---
name: generating-lwc
description: "Enforce use of Salesforce LWC MCP tools before generating any Lightning Web Component code, examples, or tests. Use when creating, modifying, reviewing, optimizing, migrating, or generating LWC code or tests, including accessibility, wire adapters, LDS/UI API, GraphQL in LWC, SLDS usage, and mobile device capabilities."
---

# Skill: lwc-development
Intent
- Enforce HARD REQUIREMENT to use Salesforce LWC MCP tools before emitting any LWC code, examples, or tests.
Trigger Conditions
- Any request that asks to create, modify, review, optimize, migrate, or generate Lightning Web Components (LWC) code or tests.
- Mentions or implications of LWC files: .js, .html, .css, .xml (.js-meta.xml), wire adapters, LDS/UI API, GraphQL in LWC, SLDS usage in LWC.
- Mobile LWC device capabilities: Barcode Scanner, Contacts, Biometrics, NFC, Location, Geofencing, Document Scanner, AR Space Capture, App Review.
Hard Requirements
Before any LWC code is produced, the agent MUST call one or more of these MCP tools based on scope:
   - General LWC guidance:
     - guide_lwc_development (mode=analysis for discovery; mode=fix if user provided code to be corrected)
     - guide_lwc_best_practices (when the goal is guidance, patterns, or conventions)
     - guide_lws_security (when security/LWS concerns are involved)
     - guide_design_general (when SLDS/UX questions exist)
   - Accessibility Guidance
     - guide_copmonent_accessibility (to audit/fix components for accessibility compliance)
   - LDS / UI API:
     - explore_lds_uiapi (to retrieve adapter API or UI API types)
     - guide_lds_development (general LDS guidance)
     - guide_lds_referential_integrity (referential integrity guidance)
     - guide_lds_data_consistency (data consistency patterns)
   - GraphQL via LDS:
     - guide_lds_graphql (MUST be called; only use its sub-tools through this orchestrator)
       - Sub-tools are NOT to be called directly: create_lds_graphql_read_query, create_lds_graphql_mutation_query, fetch_lds_graphql_schema, test_lds_graphql_query
   - Mobile features (call the specific tool BEFORE producing code):
     - create_mobile_lwc_barcode_scanner
     - create_mobile_lwc_contacts
     - create_mobile_lwc_biometrics
     - create_mobile_lwc_document_scanner
     - create_mobile_lwc_location
     - create_mobile_lwc_geofencing
     - create_mobile_lwc_nfc
     - create_mobile_lwc_ar_space_capture
     - create_mobile_lwc_app_review
   - Testing and quality:
     - orchestrate_lwc_component_testing (for end-to-end Jest test generation/validation)
     - review_lwc_jest_tests (feedback-only)
     - validate_and_optimize (UI component quality assessment runbook)
Operational Flow
- Step 1: Classify scope:
  - Mobile capability? Map to the specific mobile MCP tool(s).
  - Data via LDS/UI API? Plan explore_lds_uiapi and/or guide_lds_development.
  - GraphQL? Plan guide_lds_graphql (and follow only its orchestrated sub-tools).
  - Otherwise: guide_lwc_development (mode=analysis by default).
- Step 2: Invoke mapped tools in precedence until all applicable areas are covered:
  1) General LWC (guide_lwc_development / best practices / security / design)
  2) LDS/UI API (explore_lds_uiapi and/or guide_lds_development; add referential_integrity/data_consistency as needed)
  3) GraphQL (guide_lds_graphql; use sub-tools only through its workflow)
  4) Mobile feature tool(s)
  5) Testing/quality tools, if user requested tests or quality validation
- Step 3: If tests requested, use orchestrate_lwc_component_testing or review_lwc_jest_tests as appropriate, and include accessibility (run_lwc_accessibility_jest_tests) guidance if applicable.
Guardrails
- Prefer guide_lwc_development mode=analysis when the user request is ambiguous; switch to mode=fix when correcting provided code.