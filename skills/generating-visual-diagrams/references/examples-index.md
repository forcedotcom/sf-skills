<!-- Parent: generating-visual-diagrams/SKILL.md -->
# Examples

Example prompts and outputs for generating-visual-diagrams.

## ERD Examples

```bash
# Basic CRM ERD
gemini --yolo "/generate 'Salesforce ERD diagram: Account (blue), Contact (green), Opportunity (yellow). Show relationships with arrows. Clean white background.'"

# Custom Object ERD
gemini --yolo "/generate 'ERD diagram for custom objects: Project__c, Task__c, Resource__c. Master-detail and lookup relationships shown.'"
```

## LWC Mockup Examples

```bash
# Data Table Mockup
gemini --yolo "/generate 'Lightning datatable mockup showing Account records with columns: Name, Industry, Annual Revenue. Include search bar and pagination.'"

# Record Form Mockup
gemini --yolo "/generate 'Salesforce Lightning record form for Contact object. Show Name, Email, Phone, Account lookup fields.'"
```

## Architecture Examples

```bash
# Integration Flow
gemini --yolo "/generate 'Integration architecture diagram: Salesforce to ERP sync via MuleSoft. Show Platform Events, Named Credentials, External Services.'"
```

## Output Location

Generated images are saved to `~/nanobanana-output/`
