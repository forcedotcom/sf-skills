"""Synthetic GenAi query payloads for main pipeline integration tests.

Phase 2 Batch 1: these fixtures model the shapes live Salesforce returns
for each of the 7 Wave A + 3 Wave B SOQL calls. Field names come from
`references/soql_fields.md` (live-describe verified on my-org-alias +
my-perf-org-alias, 2026-05-02).

Two shapes covered:
  * CLASSIC_*  — MyAgent v5-shaped payloads (AiCopilot__* planner,
    InvocationTarget is DeveloperName strings, PlannerId set on bundle-
    scope functions).
  * NGA_*      — MyAgent2 v3-shaped payloads (Atlas__* planner,
    InvocationTarget is Salesforce Ids, PluginId set on every function).

SEQUENTIAL_* is a third variant: classic PlannerType but 0 plugins, 1
bundle-scope function — reproduces the SequentialPlannerIntentClassifier
bot shape which tests often miss.
"""
from __future__ import annotations


# ===========================================================================
# Classic shape (MyAgent v5-style)
# ===========================================================================

CLASSIC_PLANNER = {
    "Id": "1VxVF0000000001",
    "DeveloperName": "MyAgent",
    "MasterLabel": "Service Agent",
    "Description": "Classic ReAct MyAgent",
    "PlannerType": "AiCopilot__ReActAiPlannerV1",
    "Capabilities": None,
    "AgentGraph": None,
}

CLASSIC_PLUGINS = [
    {
        # Distinct Ids per plugin; the plugin→function join table keys on
        # this Id, so collapsing them would fan actions across every topic.
        "Id": f"1VyVF000000TOP{i}",
        "DeveloperName": f"Topic{i}",
        "MasterLabel": f"Topic {i}",
        "Description": f"Topic {i} desc",
        "PluginType": "Custom",
        "Scope": f"Topic {i} scope",
        "IsLocal": True,
        "CanEscalate": False,
        "Source": "Declarative",
        "ParentId": "1VxVF0000000001",
        "LocalDeveloperName": f"Topic{i}",
    }
    for i in range(1, 7)  # 6 topics → matches the "6 topics" assertion
]

# Classic functions: 2 bundle-scope (PlannerId set, PluginId null) +
# 2 topic-scope (PluginId set under Topic1). Invocation targets are
# DeveloperName strings (classic).
CLASSIC_FUNCTIONS = [
    # Bundle-scope
    {
        "Id": "1VuVF0000000B01",
        "DeveloperName": "LookupOrderFlow",
        "MasterLabel": "Lookup Order",
        "Description": None,
        "InvocationTargetType": "flow",
        "InvocationTarget": "LookupOrder",
        "IsLocal": False,
        "IsConfirmationRequired": False,
        "IsIncludeInProgressIndicator": False,
        "ProgressIndicatorMessage": None,
        "Source": "Declarative",
        "PluginId": None,
        "PlannerId": "1VxVF0000000001",
        "ParentId": None,
        "LocalDeveloperName": "LookupOrderFlow",
    },
    {
        "Id": "1VuVF0000000B02",
        "DeveloperName": "EscalateCase",
        "MasterLabel": "Escalate Case",
        "Description": None,
        "InvocationTargetType": "apex",
        "InvocationTarget": "CaseEscalationHandler",
        "IsLocal": False,
        "IsConfirmationRequired": True,
        "IsIncludeInProgressIndicator": False,
        "ProgressIndicatorMessage": None,
        "Source": "Declarative",
        "PluginId": None,
        "PlannerId": "1VxVF0000000001",
        "ParentId": None,
        "LocalDeveloperName": "EscalateCase",
    },
    # Topic-scope (Topic1)
    {
        "Id": "1VuVF0000000T01",
        "DeveloperName": "GetOrderDetails",
        "MasterLabel": "Get Order Details",
        "Description": None,
        "InvocationTargetType": "flow",
        "InvocationTarget": "GetOrderDetails",
        "IsLocal": True,
        "IsConfirmationRequired": False,
        "IsIncludeInProgressIndicator": True,
        "ProgressIndicatorMessage": "Looking up...",
        "Source": "Declarative",
        "PluginId": "1VyVF000000TOP1",
        "PlannerId": None,
        "ParentId": None,
        "LocalDeveloperName": "GetOrderDetails",
    },
    {
        "Id": "1VuVF0000000T02",
        "DeveloperName": "ApplyDiscount",
        "MasterLabel": "Apply Discount",
        "Description": None,
        "InvocationTargetType": "apex",
        "InvocationTarget": "DiscountApplicator",
        "IsLocal": True,
        "IsConfirmationRequired": False,
        "IsIncludeInProgressIndicator": False,
        "ProgressIndicatorMessage": None,
        "Source": "Declarative",
        "PluginId": "1VyVF000000TOP1",
        "PlannerId": None,
        "ParentId": None,
        "LocalDeveloperName": "ApplyDiscount",
    },
]

CLASSIC_PLUGIN_FUNCTIONS = [
    {"Id": "1VqVF000001", "PluginId": "1VyVF000000TOP1", "Function": "1VuVF0000000T01"},
    {"Id": "1VqVF000002", "PluginId": "1VyVF000000TOP1", "Function": "1VuVF0000000T02"},
]

CLASSIC_BUNDLE_FN_JOIN = [
    {"Id": "1VrVF000001", "PlannerId": "1VxVF0000000001", "Plugin": "LookupOrderFlow"},
    {"Id": "1VrVF000002", "PlannerId": "1VxVF0000000001", "Plugin": "EscalateCase"},
]

CLASSIC_INSTRUCTIONS = [
    {
        "Id": "1VwVF000001",
        "GenAiPluginDefinitionId": "1VyVF000000TOP1",
        "DeveloperName": "Instruction1",
        "MasterLabel": "Use polite tone",
        "Description": "Always greet the user first.",
        "SortOrder": 1,
    }
]

CLASSIC_ATTRS = [
    {
        "Id": "1VvVF000001",
        "ParentId": "1VuVF0000000T01",
        "DeveloperName": "OrderId",
        "MasterLabel": "Order Id",
        "Description": None,
        "MappingType": "input",
        "ParameterName": "orderId",
    }
]

# Wave B classic: 2 flows (LookupOrder, GetOrderDetails), 2 apex
# (CaseEscalationHandler, DiscountApplicator).
CLASSIC_FLOW_DEFS = [
    {"Id": "300VF001", "DeveloperName": "LookupOrder", "ActiveVersionId": "301VF001"},
    {"Id": "300VF002", "DeveloperName": "GetOrderDetails", "ActiveVersionId": "301VF002"},
]

CLASSIC_APEX_ROWS = [
    {
        "Id": "01pVF001",
        "Name": "CaseEscalationHandler",
        "Body": "public class CaseEscalationHandler {}",
        "SymbolTable": None,
        "ApiVersion": 60.0,
        "IsValid": True,
    },
    {
        "Id": "01pVF002",
        "Name": "DiscountApplicator",
        "Body": "public class DiscountApplicator {}",
        "SymbolTable": None,
        "ApiVersion": 60.0,
        "IsValid": True,
    },
]

CLASSIC_FLOW_METADATA = {
    "301VF001": {"Id": "301VF001", "FullName": "LookupOrder-1", "Metadata": {}},
    "301VF002": {"Id": "301VF002", "FullName": "GetOrderDetails-1", "Metadata": {}},
}


# ===========================================================================
# NGA shape (MyAgent2 v3-style) — InvocationTarget is Ids, PluginId-only
# ===========================================================================

NGA_PLANNER = {
    "Id": "1VxVF0000000N01",
    "DeveloperName": "MyAgent2",
    "MasterLabel": "NGA Service Agent",
    "Description": "Atlas MyAgent",
    "PlannerType": "Atlas__ConcurrentMultiAgentOrchestration",
    "Capabilities": None,
    "AgentGraph": None,
}

NGA_PLUGINS = [
    {
        "Id": "1VyVF0000000N01",
        "DeveloperName": "NGATopic1",
        "MasterLabel": "NGA Topic 1",
        "Description": None,
        "PluginType": "Custom",
        "Scope": "NGA scope",
        "IsLocal": True,
        "CanEscalate": False,
        "Source": "Declarative",
        "ParentId": "1VxVF0000000N01",
        "LocalDeveloperName": "NGATopic1",
    },
]

# NGA functions store InvocationTarget as Salesforce Ids — `01p...` for
# Apex, `300...` for FlowDefinition. PluginId is always set; PlannerId
# is null.
NGA_FUNCTIONS = [
    {
        "Id": "1VuVF0000000N01",
        "DeveloperName": "NGAFlowAction",
        "MasterLabel": "NGA Flow Action",
        "Description": None,
        "InvocationTargetType": "flow",
        "InvocationTarget": "300VF999NGAFLOW",
        "IsLocal": True,
        "IsConfirmationRequired": False,
        "IsIncludeInProgressIndicator": False,
        "ProgressIndicatorMessage": None,
        "Source": "Declarative",
        "PluginId": "1VyVF0000000N01",
        "PlannerId": None,
        "ParentId": None,
        "LocalDeveloperName": "NGAFlowAction",
    },
    {
        "Id": "1VuVF0000000N02",
        "DeveloperName": "NGAApexAction",
        "MasterLabel": "NGA Apex Action",
        "Description": None,
        "InvocationTargetType": "apex",
        "InvocationTarget": "01pVF999NGAAPEX",
        "IsLocal": True,
        "IsConfirmationRequired": False,
        "IsIncludeInProgressIndicator": False,
        "ProgressIndicatorMessage": None,
        "Source": "Declarative",
        "PluginId": "1VyVF0000000N01",
        "PlannerId": None,
        "ParentId": None,
        "LocalDeveloperName": "NGAApexAction",
    },
]

NGA_PLUGIN_FUNCTIONS = [
    {"Id": "1VqVF00N01", "PluginId": "1VyVF0000000N01", "Function": "1VuVF0000000N01"},
    {"Id": "1VqVF00N02", "PluginId": "1VyVF0000000N01", "Function": "1VuVF0000000N02"},
]

# NGA reverse-lookup rows (B1 NGA variant + B3 NGA variant)
NGA_FLOW_DEF_BY_ID = [
    {
        "Id": "300VF999NGAFLOW",
        "DeveloperName": "NGAResolvedFlow",
        "ActiveVersionId": "301VF999NGAVER",
        "LatestVersionId": "301VF999NGAVER",
    },
]

NGA_APEX_BY_ID = [
    {
        "Id": "01pVF999NGAAPEX",
        "Name": "NGAResolvedApex",
        "Body": "public class NGAResolvedApex {}",
        "SymbolTable": None,
        "ApiVersion": 60.0,
        "IsValid": True,
    },
]


# ===========================================================================
# SequentialPlannerIntentClassifier shape
# ===========================================================================
# Classic family (AiCopilot__SequentialPlannerIntentClassifier), ZERO
# plugins, exactly ONE bundle-scope function. Tests the
# "empty plugin_ids short-circuits" path.

SEQ_PLANNER = {
    "Id": "1VxVF0000000SEQ",
    "DeveloperName": "SequentialAgent",
    "MasterLabel": "Sequential Agent",
    "Description": None,
    "PlannerType": "AiCopilot__SequentialPlannerIntentClassifier",
    "Capabilities": None,
    "AgentGraph": None,
}

SEQ_FUNCTIONS = [
    {
        "Id": "1VuVF0000000S01",
        "DeveloperName": "StandardReply",
        "MasterLabel": "Standard Reply",
        "Description": None,
        "InvocationTargetType": "standardInvocableAction",
        "InvocationTarget": "reply",
        "IsLocal": False,
        "IsConfirmationRequired": False,
        "IsIncludeInProgressIndicator": False,
        "ProgressIndicatorMessage": None,
        "Source": "Declarative",
        "PluginId": None,
        "PlannerId": "1VxVF0000000SEQ",
        "ParentId": None,
        "LocalDeveloperName": "StandardReply",
    },
]


# ===========================================================================
# Bot version / definition rows (Data API shape)
# ===========================================================================

def make_bot_versions(agent_api_name: str, versions=("v5",), active: str = "v5") -> list[dict]:
    """Build BotVersion records list in the Data API shape."""
    return [
        {
            "Id": f"0Xx{i:012d}",
            "DeveloperName": v,
            "Status": "Active" if v == active else "Inactive",
            "BotDefinitionId": "0Xa000000000ABC",
            "BotDefinition": {
                "DeveloperName": agent_api_name,
                "MasterLabel": f"{agent_api_name} bot",
            },
        }
        for i, v in enumerate(versions)
    ]


BOT_DEFINITION_DETAIL_CLASSIC = {
    "DeveloperName": "MyAgent",
    "MasterLabel": "Service Agent",
    "Description": "Classic bot",
    "AgentType": "ExternalCopilot",
    "Type": "Copilot",
    "AgentTemplate": "EinsteinCopilotForServiceTmpl",
    "BotSource": "EinsteinCopilot",
}

BOT_DEFINITION_DETAIL_NGA = {
    "DeveloperName": "MyAgent2",
    "MasterLabel": "NGA Service Agent",
    "Description": "NGA bot",
    "AgentType": "EinsteinAgentKind",
    "Type": "Agentforce",
    "AgentTemplate": "SvcCopilotTmpl__EinsteinAgentKind",
    "BotSource": "AgentforceService",
}


# ===========================================================================
# Probe-channels "all OK" + "PROBE_FAILED" payloads
# ===========================================================================


def probe_ok_payload() -> dict:
    return {
        "_schema": "channels/1",
        "_built_at_utc": 0.0,
        "status": "OK",
        "channels": {},
    }


def probe_failed_payload(sobject: str = "GenAiPlannerDefinition",
                        missing: list[str] | None = None) -> dict:
    return {
        "_schema": "channels/1",
        "_built_at_utc": 0.0,
        "status": "PROBE_FAILED",
        "channels": {
            sobject: {
                "queryable_fields": [],
                "mandatory_missing": missing or ["DeveloperName"],
                "describe_error": None,
            }
        },
    }
