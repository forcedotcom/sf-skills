# Architecture Template: Integration Flow

## Prompt Template

```
Professional Salesforce integration architecture diagram:

SYSTEMS:
[List systems with types and icons]

INTEGRATION PATTERNS:
[List integrations with protocols and directions]

COMPONENTS:
- API Gateway (if applicable)
- Authentication layer
- Middleware/ESB (if applicable)
- Error handling/retry logic

STYLING:
- Cloud icon for Salesforce
- Server icons for external systems
- Arrows with protocol labels
- Color coding by system type
- Professional diagram style

FORMAT:
- Landscape orientation
- Left-to-right or hub-spoke layout
- Include legend
```

## Example

```bash
gemini "/generate 'Salesforce integration architecture diagram:

Systems:
1. Salesforce (cloud icon, blue)
2. MuleSoft (middleware icon, purple)
3. SAP ERP (server icon, orange)

Flows:
1. Salesforce --REST--> MuleSoft --BAPI--> SAP
   - Account/Contact sync (bidirectional)

2. SAP --Events--> MuleSoft --Platform Events--> Salesforce
   - Invoice updates

Include:
- OAuth 2.0 authentication badges
- Error queue for failed messages

Style: Professional, clean lines, pastel colors'"
```
