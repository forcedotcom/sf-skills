# Attribute-routing Tooling API contract

Live API v68 describe validation confirms Tooling API CRUD for `WorkSkillRouting` and `WorkSkillRoutingAttribute` on orgs provisioned for Skills-Based Routing. A rule is created inactive, populated with one or more child mappings, and activated only when complete.

`PATCH WorkSkillRouting/{Id}` replaces the entire Metadata compound. Always read first, preserve `masterLabel`, `relatedEntity`, and `workSkillRoutingAttributes`, remove the read-only `urls` member, then write the complete compound. Omitting the nested mappings deletes them.

Eligible related entities are Case, ChangeRequest, ContactRequest, FlowOrchestrationWorkItem, Incident, Lead, LiveChatTranscript, MessagingSession, Order, Problem, SocialPost, VoiceCall, and WorkOrder. `SkillLevel` is 0–10. `SkillPriority` is 0–4 and is valid only when `IsAdditionalSkill=true`.
