"""Generate @isTest companion classes for scaffolded Apex InvocableMethod actions."""

from __future__ import annotations

from scripts.generators.apex_stub import _TYPE_MAP, _COMPLEX_TYPE_MAP, generate_apex_meta_xml


# Type-appropriate placeholder values for test data
_TEST_PLACEHOLDERS = {
    "String": "'test'",
    "Decimal": "1",
    "Integer": "1",
    "Double": "1.0",
    "Boolean": "true",
    "Date": "Date.today()",
    "Datetime": "Datetime.now()",
    "Id": "null",
    "Map<String, Object>": "new Map<String, Object>()",
    "List<Object>": "new List<Object>()",
    "SObject": "new Account()",
}


def _placeholder_for_type(apex_type: str) -> str:
    """Return a type-appropriate placeholder value for test data."""
    return _TEST_PLACEHOLDERS.get(apex_type, "null")


def _resolve_apex_type(param: dict) -> str:
    """Resolve a parameter dict to its Apex type string."""
    return _COMPLEX_TYPE_MAP.get(
        param.get("complex_data_type_name", ""),
        _TYPE_MAP.get(param.get("type", "string"), "String"),
    )


def generate_apex_test_class(
    class_name: str,
    inputs: list[dict] | None = None,
    outputs: list[dict] | None = None,
    is_callout: bool = False,
) -> str:
    """Generate an @isTest companion class for an Apex InvocableMethod stub.

    Args:
        class_name: The production Apex class name (test class will be {class_name}Test).
        inputs: Action input definitions (list of dicts with 'name', 'type' keys).
        outputs: Action output definitions (list of dicts with 'name', 'type' keys).
        is_callout: If True, include HttpCalloutMock inner class.

    Returns:
        Apex test class source code string.
    """
    inputs = inputs or []
    outputs = outputs or []
    test_name = f"{class_name}Test"

    lines = [
        "@isTest",
        f"private class {test_name} {{",
    ]

    # HttpCalloutMock inner class for callout actions
    if is_callout:
        lines.extend([
            "",
            "    private class MockHttpResponse implements HttpCalloutMock {",
            "        public HttpResponse respond(HttpRequest req) {",
            "            HttpResponse res = new HttpResponse();",
            "            res.setHeader('Content-Type', 'application/json');",
            "            res.setBody('{\"status\": \"ok\"}');",
            "            res.setStatusCode(200);",
            "            return res;",
            "        }",
            "    }",
        ])

    # Test method
    lines.extend([
        "",
        "    @isTest",
        "    static void testInvoke() {",
    ])

    if is_callout:
        lines.append("        Test.setMock(HttpCalloutMock.class, new MockHttpResponse());")
        lines.append("")

    # Build request
    lines.append(f"        {class_name}.Request req = new {class_name}.Request();")
    for inp in inputs:
        apex_type = _resolve_apex_type(inp)
        placeholder = _placeholder_for_type(apex_type)
        lines.append(f"        req.{inp['name']} = {placeholder};")

    # Invoke
    lines.extend([
        "",
        f"        List<{class_name}.Response> results = {class_name}.invoke(",
        f"            new List<{class_name}.Request>{{ req }}",
        "        );",
        "",
        "        System.assertNotEquals(null, results, 'Expected non-null response');",
        "        System.assertEquals(1, results.size(), 'Expected one response');",
    ])

    # Assert outputs are populated
    if outputs:
        lines.append("")
        lines.append(f"        {class_name}.Response resp = results[0];")
        for out in outputs:
            apex_type = _resolve_apex_type(out)
            if apex_type == "String":
                lines.append(f"        System.assertNotEquals(null, resp.{out['name']}, 'Expected {out['name']} to be set');")

    lines.extend([
        "    }",
        "}",
    ])

    return "\n".join(lines) + "\n"
