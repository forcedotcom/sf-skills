# Complete Agent Examples

> Extracted from SKILL.md Sections 9 + 10. This file is loaded on demand when complete agent examples are needed.

## Minimal Service Agent

This is the absolute minimum for a deployable service agent:

```
system:
	instructions: "You are a helpful customer service agent."
	messages:
		welcome: "Hello! How can I help you today?"
		error: "Something went wrong. Please try again."

config:
	developer_name: "MinimalAgent"
	agent_label: "Minimal Agent"
	description: "A minimal service agent"
	default_agent_user: "agent@00dxx000001234.ext"

variables:
	EndUserId: linked string
		source: @MessagingSession.MessagingEndUserId
		description: "Messaging End User ID"
		visibility: "External"
	RoutableId: linked string
		source: @MessagingSession.Id
		description: "Messaging Session ID"
		visibility: "External"
	ContactId: linked string
		source: @MessagingEndUser.ContactId
		description: "Contact ID"
		visibility: "External"

language:
	default_locale: "en_US"
	additional_locales: ""
	all_additional_locales: False

start_agent topic_selector:
	description: "Begin the onboarding flow"

topic greeting:
	label: "Greeting"
	description: "Greet users and provide help"
	reasoning:
		instructions: ->
			| Welcome the user warmly.
			| Ask how you can help them today.
```

Companion `bundle-meta.xml` (MUST be this exact content -- no extra fields):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<AiAuthoringBundle xmlns="http://soap.sforce.com/2006/04/metadata">
  <bundleType>AGENT</bundleType>
</AiAuthoringBundle>
```

---

## Minimal Employee Agent

Employee agents differ from service agents in their config, variables, and connection blocks. This example shows a 2-topic IT Knowledge agent deployed to internal employees.

```
system:
	instructions: |
		You are an AI-powered IT assistant for Acme Corp employees.
		Help employees find answers to common IT questions and
		look up knowledge articles.
		You are an AI assistant, not a human.
	messages:
		welcome: "Hi! I'm the IT Help assistant. What can I help you with?"
		error: "Something went wrong. Please try again."

config:
	developer_name: "IT_Knowledge_Agent"
	agent_label: "IT Knowledge Agent"
	description: "Internal IT knowledge base assistant for employees"
	agent_type: "AgentforceEmployeeAgent"
	# NOTE: No default_agent_user — employee agents run as the logged-in user.
	# No connection messaging: block — employee agents have no messaging channel.
	# No MessagingSession linked variables — those are service-agent-only.

variables:
	search_query: mutable string = ""
		description: "Current search query"
	article_id: mutable string = ""
		description: "Selected knowledge article ID"

language:
	default_locale: "en_US"
	additional_locales: ""
	all_additional_locales: False

start_agent topic_selector:
	description: "Route employees to the right IT support topic"
	reasoning:
		instructions: |
			You are a router only. Do NOT answer questions directly.
			Always use a transition action to route immediately.
			- IT questions, troubleshooting, how-to -> use to_knowledge
			- Password reset, account access -> use to_account
		actions:
			to_knowledge: @utils.transition to @topic.knowledge_search
				description: "Search IT knowledge base"
			to_account: @utils.transition to @topic.account_support
				description: "Account and password help"

topic knowledge_search:
	label: "Knowledge Search"
	description: "Search and retrieve IT knowledge articles"

	actions:
		search_articles:
			description: "Search knowledge base for articles"
			target: "apex://ITKnowledge.searchArticles"
			inputs:
				query: string
					description: "Search query"
			outputs:
				articles: string
					description: "Matching articles as JSON"
					is_displayable: True

	reasoning:
		instructions: ->
			if @variables.article_id != "":
				| Found article {!@variables.article_id}. Here are the details.

			| Search the knowledge base using the search_articles action.
			| Present results clearly. Do not fabricate article content.

		actions:
			search: @actions.search_articles
				description: "Search knowledge base"
				with query = ...
				set @variables.search_query = @outputs.articles

			back: @utils.transition to @topic.topic_selector
				description: "Route to a different topic"

topic account_support:
	label: "Account Support"
	description: "Help with password resets and account access"

	actions:
		reset_password:
			description: "Initiate password reset for employee"
			target: "flow://IT_Password_Reset"
			inputs:
				employee_email: string
					description: "Employee email address"
			outputs:
				status: string
					description: "Reset status"
					is_displayable: True

	reasoning:
		instructions: ->
			| I can help with password resets and account access.
			| Ask for the employee's email, then use the reset_password action.

		actions:
			reset: @actions.reset_password
				description: "Reset employee password"
				with employee_email = ...

			# NOTE: No @utils.escalate — employee agents cannot escalate to
			# human agents via messaging. Use a transition or case-creation
			# action instead.
			back: @utils.transition to @topic.topic_selector
				description: "Route to a different topic"
```

**What's deliberately absent (vs. service agents):**
- No `default_agent_user` in config (agent runs as logged-in employee)
- No `connection messaging:` block (no messaging channel)
- No `EndUserId`/`RoutableId`/`ContactId` linked variables (no `@MessagingSession`)
- No `@utils.escalate` action (requires `connection messaging:`)

---

## Multi-Topic Agent with Actions

```
system:
	instructions: |
		You are a customer service agent for TechCorp.
		Be professional, concise, and solution-oriented.
		Always verify the customer before sensitive operations.
	messages:
		welcome: "Welcome to TechCorp Support! How can I assist you?"
		error: "I apologize for the issue. Please try again."

config:
	developer_name: "TechCorpAgent"
	agent_label: "TechCorp Support Agent"
	description: "Handles order inquiries, returns, and general support"
	default_agent_user: "einstein@00dxx000001234.ext"

variables:
	EndUserId: linked string
		source: @MessagingSession.MessagingEndUserId
		description: "Messaging End User ID"
		visibility: "External"
	RoutableId: linked string
		source: @MessagingSession.Id
		description: "Messaging Session ID"
		visibility: "External"
	ContactId: linked string
		source: @MessagingEndUser.ContactId
		description: "Contact ID"
		visibility: "External"
	order_id: mutable string = ""
		description: "Current order being discussed"
	order_status: mutable string = ""
		description: "Status of the current order"
	is_verified: mutable boolean = False
		description: "Customer verification status"
	case_id: mutable string = ""
		description: "Created case ID"

language:
	default_locale: "en_US"
	additional_locales: ""
	all_additional_locales: False

start_agent topic_selector:
	description: "Route customers to the right support topic"
	reasoning:
		instructions: |
			You are a router only. Do NOT answer questions or provide help directly.
			Always use a transition action to route to the correct topic immediately.
			- Order status or tracking -> use to_orders
			- Returns or refunds -> use to_returns
			- General questions -> use to_general
			Never attempt to help the customer yourself. Always route.
		actions:
			to_orders: @utils.transition to @topic.order_support
				description: "Check order status or tracking"
			to_returns: @utils.transition to @topic.return_support
				description: "Process a return or refund"
			to_general: @utils.transition to @topic.general_support
				description: "General questions and support"

topic order_support:
	label: "Order Support"
	description: "Handle order status and tracking inquiries"

	actions:
		get_order:
			description: "Look up order by ID"
			target: "flow://Get_Order_Status"
			inputs:
				order_id: string
					description: "Order ID"
			outputs:
				status: string
					description: "Order status"
					is_displayable: True
				tracking_url: string
					description: "Tracking URL"
					is_displayable: True

	reasoning:
		instructions: ->
			if @variables.order_status != "":
				| Order {!@variables.order_id} status: {!@variables.order_status}

			| What is your order number? I will look it up for you.
			| Use the get_order action to retrieve order details.
			| Do not guess order status -- always use the action result.

		actions:
			lookup: @actions.get_order
				description: "Look up order"
				with order_id = ...
				set @variables.order_id = @outputs.order_id
				set @variables.order_status = @outputs.status

			back: @utils.transition to @topic.topic_selector
				description: "Route to a different topic"

topic return_support:
	label: "Return Support"
	description: "Handle returns and refund requests"

	actions:
		initiate_return:
			description: "Start a return process"
			target: "flow://Initiate_Return"
			inputs:
				order_id: string
					description: "Order ID for the return"
				reason: string
					description: "Reason for return"
			outputs:
				return_id: string
					description: "Return authorization ID"
					is_displayable: True

	reasoning:
		instructions: ->
			| I can help with your return request.
			| Please provide your order number and the reason for the return.
			| Use the initiate_return action to start the process -- do not fabricate return IDs.

		actions:
			start_return: @actions.initiate_return
				description: "Start a return"
				with order_id = ...
				with reason = ...
				set @variables.case_id = @outputs.return_id

			back: @utils.transition to @topic.topic_selector
				description: "Route to a different topic"

	after_reasoning:
		if @variables.case_id != "":
			transition to @topic.confirmation

topic general_support:
	label: "General Support"
	description: "Handle general support questions"
	reasoning:
		instructions: |
			Help the customer with general questions.
			If the question is about orders or returns, route appropriately.
		actions:
			escalate_now: @utils.escalate
				description: "Transfer to human agent"
			back: @utils.transition to @topic.topic_selector
				description: "Route to a different topic"

topic confirmation:
	label: "Confirmation"
	description: "Confirm the completed action"
	reasoning:
		instructions: ->
			| Your request has been processed. Reference: {!@variables.case_id}
			| Is there anything else I can help with?
		actions:
			new_request: @utils.transition to @topic.topic_selector
				description: "Start a new request"
			end_chat: @actions.end_conversation
				description: "End the conversation"
```
