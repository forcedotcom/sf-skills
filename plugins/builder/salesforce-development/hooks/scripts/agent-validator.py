#!/usr/bin/env python3
"""PostToolUse hook: validate .agent files for syntax errors after Write/Edit.

Checks:
1. Mixed tabs and spaces within a single file (compilation error)
2. Lowercase booleans (must be True/False)
3. Required blocks (system, config, start_agent)
4. Config fields: developer_name (preferred over agent_name), default_agent_user.
5. Variables declared as both mutable AND linked
6. Undefined topic references in transitions
7. start_agent target references a defined topic
8. developer_name matches folder name
9. Reserved field names used as variable names
10. @inputs in set clauses (must use @outputs)
11. bundle-meta.xml extra fields that break publish
12. `default:` sub-property on variables (must use inline `= value`)
13. `type:` sub-property on action I/O fields (must use inline type)
14. Linked variable source using `$Context` instead of `@MessagingSession`/`@MessagingEndUser`
15. Invalid `connection:` block (must be `connection messaging:`)
16. Nested `description:` under slot-fill `...` token
17. Redundant routing/menu topics that duplicate start_agent

Safety/content review is handled by the /adlc-safety skill (LLM-driven, not regex).

Also auto-resolves REPLACE_WITH_EINSTEIN_AGENT_USER placeholder by querying the org.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from stdin_utils import read_stdin_safe
except ImportError:
    def read_stdin_safe(timeout_seconds=0.1):
        if sys.stdin.isatty():
            return {}
        try:
            return json.load(sys.stdin)
        except Exception:
            return {}


# Reserved field names that cause parse errors
RESERVED_NAMES = {
    "description", "label", "is_required", "is_displayable",
    "default", "name", "type", "source", "visibility",
}


class AgentScriptValidator:
    """Validates .agent file syntax and structure."""

    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.lines = content.splitlines()
        self.errors: list[tuple[int, str, str]] = []  # (line_num, severity, message)
        self.warnings: list[tuple[int, str, str]] = []

    def validate(self) -> dict:
        """Run all validations and return result dict."""
        self._check_mixed_indentation()
        self._check_boolean_case()
        self._check_required_blocks()
        self._check_config_fields()
        self._check_variable_modifiers()
        self._check_topic_references()
        self._check_start_agent_target()
        self._check_folder_name_match()
        self._check_reserved_field_names()
        self._check_inputs_in_set()
        self._check_bundle_meta_xml()
        self._check_default_subproperty()
        self._check_type_subproperty()
        self._check_numeric_action_io()
        self._check_linked_var_source()
        self._check_connection_block()
        self._check_slot_fill_description()
        self._check_apex_target_shared_class()
        self._check_redundant_routing_topic()
        self._auto_resolve_placeholder()

        return {
            "success": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "file_path": self.file_path,
        }

    def _check_mixed_indentation(self):
        """Check for mixed tabs and spaces within a single file (compilation error).

        The Agent Script compiler (`sf agent validate authoring-bundle`) accepts
        either tabs OR spaces for indentation, but mixing both in the same file
        causes parse errors. Space-only and tab-only files both compile cleanly.
        """
        has_tabs = False
        has_spaces = False
        for i, line in enumerate(self.lines, 1):
            if line.startswith("\t"):
                has_tabs = True
            elif line.startswith("    ") and line.strip():
                has_spaces = True

        if has_tabs and has_spaces:
            self.errors.append((0, "ERROR", "Mixed tabs and spaces — pick one style per file (Agent Script accepts either, but not both)"))

    def _check_boolean_case(self):
        """Check for lowercase booleans (must be True/False)."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            # Skip comments and strings
            if stripped.startswith("#") or stripped.startswith("//"):
                continue
            # Check for lowercase true/false outside of quoted strings.
            # Booleans inside quoted values (JSON/SOQL examples, prose) are data,
            # not Agent Script literals, so strip quoted substrings before matching.
            unquoted = re.sub(r'"[^"]*"|\'[^\']*\'', "", stripped)
            # Match: = true, = false, : true, : false
            if re.search(r'[=:]\s*\btrue\b', unquoted):
                self.errors.append((i, "ERROR", f"Lowercase 'true' — use 'True' (line {i})"))
            if re.search(r'[=:]\s*\bfalse\b', unquoted):
                self.errors.append((i, "ERROR", f"Lowercase 'false' — use 'False' (line {i})"))

    def _check_required_blocks(self):
        """Check for required top-level blocks."""
        required = {"system": False, "config": False, "start_agent": False}
        has_topic = False

        for line in self.lines:
            stripped = line.strip()
            if stripped.startswith("system:"):
                required["system"] = True
            elif stripped.startswith("config:"):
                required["config"] = True
            elif stripped.startswith("start_agent ") or stripped.startswith("start_agent:"):
                required["start_agent"] = True
            elif stripped.startswith("topic "):
                has_topic = True

        for block, found in required.items():
            if not found:
                self.errors.append((0, "ERROR", f"Missing required block: {block}"))

    def _check_config_fields(self):
        """Check config block for required fields."""
        in_config = False
        config_fields = set()

        for line in self.lines:
            stripped = line.strip()
            if stripped.startswith("config:"):
                in_config = True
                continue
            if in_config:
                if stripped and not stripped.startswith("#") and not line.startswith(("\t", " ")):
                    in_config = False
                    continue
                field_match = re.match(r'(\w+):', stripped)
                if field_match:
                    config_fields.add(field_match.group(1))

        # developer_name is preferred; agent_name is accepted as legacy
        if "developer_name" not in config_fields:
            if "agent_name" in config_fields:
                self.warnings.append((0, "WARN",
                    "Config uses 'agent_name' — prefer 'developer_name' (must match folder name)"))
            else:
                self.warnings.append((0, "WARN", "Missing config field: developer_name"))

        if "default_agent_user" not in config_fields:
            self.warnings.append((0, "WARN", "Missing config field: default_agent_user"))

    def _check_variable_modifiers(self):
        """Check that variables aren't declared as both mutable AND linked."""
        for i, line in enumerate(self.lines, 1):
            if "mutable" in line and "linked" in line:
                self.errors.append((i, "ERROR", f"Variable declared as both mutable AND linked (line {i})"))

    def _check_topic_references(self):
        """Check that @topic.X references resolve to defined topics."""
        # Collect defined topics
        defined_topics = set()
        for line in self.lines:
            match = re.match(r'^(?:start_agent|topic)\s+(\w+):', line.strip())
            if match:
                defined_topics.add(match.group(1))

        # Check references
        for i, line in enumerate(self.lines, 1):
            for ref_match in re.finditer(r'@topic\.(\w+)', line):
                topic_name = ref_match.group(1)
                if topic_name not in defined_topics:
                    self.warnings.append((i, "WARN", f"Undefined topic reference: @topic.{topic_name} (line {i})"))

    def _check_start_agent_target(self):
        """Check that start_agent references a defined topic.

        Two valid syntaxes:
        - `start_agent: topic_name`  → references a separate topic (must exist)
        - `start_agent name:`        → inline entry block definition (no separate topic needed)
        """
        start_target = None
        start_line = 0
        is_inline = False

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            # `start_agent: topic_name` — reference to a separate topic
            ref_match = re.match(r'^start_agent\s*:\s*(\w+)\s*$', stripped)
            if ref_match:
                start_target = ref_match.group(1)
                start_line = i
                is_inline = False
                break
            # `start_agent name:` — inline entry block definition
            inline_match = re.match(r'^start_agent\s+(\w+)\s*:', stripped)
            if inline_match:
                start_target = inline_match.group(1)
                start_line = i
                is_inline = True
                break

        if not start_target:
            return  # Missing start_agent caught by _check_required_blocks

        # Inline definitions don't need a separate topic
        if is_inline:
            return

        # Reference-style must point to a defined topic
        defined_topics = set()
        for line in self.lines:
            match = re.match(r'^topic\s+(\w+):', line.strip())
            if match:
                defined_topics.add(match.group(1))

        if start_target not in defined_topics:
            self.errors.append((start_line, "ERROR",
                f"start_agent references '{start_target}' but no 'topic {start_target}:' is defined (line {start_line})"))

    def _check_folder_name_match(self):
        """Check that developer_name (or agent_name) matches the folder name."""
        # Extract developer_name or agent_name from config
        agent_name = None
        field_used = None
        for line in self.lines:
            match = re.match(r'\s*developer_name:\s*"?([^"\s]+)"?', line.strip())
            if match:
                agent_name = match.group(1)
                field_used = "developer_name"
                break
            match = re.match(r'\s*agent_name:\s*"?([^"\s]+)"?', line.strip())
            if match:
                agent_name = match.group(1)
                field_used = "agent_name"
                break

        if agent_name:
            folder_name = Path(self.file_path).parent.name
            if folder_name != agent_name:
                self.warnings.append((0, "WARN", f"{field_used} '{agent_name}' doesn't match folder name '{folder_name}'"))

    def _check_reserved_field_names(self):
        """Check for reserved field names used as variable or action parameter names."""
        in_variables = False
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("variables:"):
                in_variables = True
                continue
            if in_variables and stripped and not line.startswith(("\t", " ")):
                in_variables = False

            if in_variables:
                var_match = re.match(r'(\w+):\s*(?:mutable|linked)', stripped)
                if var_match and var_match.group(1) in RESERVED_NAMES:
                    self.errors.append((i, "ERROR", f"Reserved field name '{var_match.group(1)}' used as variable name (line {i})"))

    def _check_inputs_in_set(self):
        """Check for @inputs in set clauses (must use @outputs instead)."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r'\bset\b.*@inputs\.', stripped):
                self.errors.append((i, "ERROR",
                    f"'@inputs' in set clause — use '@outputs' instead (line {i})"))

    def _check_bundle_meta_xml(self):
        """Check companion bundle-meta.xml for extra fields that break publish."""
        meta_path = Path(self.file_path).with_suffix(".bundle-meta.xml")
        if not meta_path.exists():
            # Also check parent dir for <name>.bundle-meta.xml
            parent = Path(self.file_path).parent
            agent_stem = Path(self.file_path).stem
            meta_path = parent / f"{agent_stem}.bundle-meta.xml"
            if not meta_path.exists():
                return

        try:
            meta_content = meta_path.read_text(encoding="utf-8")
        except (IOError, OSError):
            return

        # Check for fields that cause "Required fields missing: [BundleType]" on publish
        bad_fields = []
        for field in ["<developerName>", "<masterLabel>", "<description>", "<label>"]:
            if field in meta_content:
                bad_fields.append(field)

        if bad_fields:
            self.errors.append((0, "ERROR",
                f"bundle-meta.xml has extra fields {bad_fields} — "
                f"MUST contain only <bundleType>AGENT</bundleType>. "
                f"Extra fields cause 'Required fields missing: [BundleType]' on publish"))

        if "<bundleType>" not in meta_content:
            self.errors.append((0, "ERROR",
                "bundle-meta.xml missing <bundleType>AGENT</bundleType> — required for publish"))

    def _check_default_subproperty(self):
        """Check for `default:` used as a sub-property of mutable variables.

        The compiler rejects `default:` as a standalone sub-property.
        Correct syntax: `varName: mutable string = ""`  (inline default)
        Wrong syntax:   `varName: mutable string` + `default: ""`  (sub-property)
        """
        in_variables = False
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("variables:"):
                in_variables = True
                continue
            # Exit variables block when we hit a non-indented, non-empty line
            if in_variables and stripped and not line.startswith(("\t", " ")):
                in_variables = False

            if in_variables and re.match(r'default:\s', stripped):
                self.errors.append((i, "ERROR",
                    f"'default:' sub-property is invalid — use inline default "
                    f"(e.g., `varName: mutable string = \"\"`) (line {i})"))

    def _check_type_subproperty(self):
        """Check for `type:` used as a sub-property in action input/output blocks.

        The compiler rejects nested `type: string` under I/O field names.
        Correct syntax: `fieldName: string`  (inline type)
        Wrong syntax:   `fieldName:` + `type: string`  (sub-property)
        """
        in_inputs_outputs = False
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped in ("inputs:", "outputs:"):
                in_inputs_outputs = True
                continue
            # Exit I/O block when indent level drops back
            if in_inputs_outputs and stripped and not line.startswith(("\t\t\t", "         ")):
                # If we're at a higher-level block, exit
                if not stripped.startswith(("#", "//")) and ":" in stripped:
                    # Check if this is still inside actions (3+ tab indent)
                    tab_count = len(line) - len(line.lstrip("\t"))
                    if tab_count < 3:
                        in_inputs_outputs = False

            if in_inputs_outputs and re.match(r'type:\s', stripped):
                self.errors.append((i, "ERROR",
                    f"'type:' sub-property in action I/O is invalid — use inline type "
                    f"(e.g., `fieldName: string`) (line {i})"))

    def _check_numeric_action_io(self):
        """Check for bare 'number' type in action inputs/outputs.

        Action I/O requires object + complex_data_type_name for numeric types.
        Bare 'number' works for variables but fails in action I/O at deploy time.
        """
        in_action_io = False
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            tab_count = len(line) - len(line.lstrip("\t"))

            # Detect inputs:/outputs: blocks at action depth (3+ tabs)
            if stripped in ("inputs:", "outputs:") and tab_count >= 3:
                in_action_io = True
                continue

            # Exit action I/O block when indent drops
            if in_action_io and stripped and tab_count < 4:
                in_action_io = False

            # Check for bare number type in action I/O
            if in_action_io and re.match(r'\w+:\s*number\s*$', stripped):
                field_name = stripped.split(":")[0].strip()
                self.warnings.append((i, "WARN",
                    f"Action I/O field '{field_name}' uses bare 'number' type (line {i}) — "
                    f"use 'object' with complex_data_type_name: \"lightning__integerType\" "
                    f"or \"lightning__doubleType\" instead. Bare 'number' causes publish failures."))

    def _check_linked_var_source(self):
        """Check that linked variable source uses @ references, not $Context."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("source:") and "$Context" in stripped:
                self.errors.append((i, "ERROR",
                    f"Linked variable source uses '$Context' (line {i}) — "
                    f"use @MessagingSession.* or @MessagingEndUser.* references instead"))

    def _check_connection_block(self):
        """Check that connection block uses 'connection messaging:' syntax."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped == "connection:":
                self.errors.append((i, "ERROR",
                    f"Invalid 'connection:' block (line {i}) — "
                    f"use 'connection messaging:' with routing_type inside"))

    def _check_slot_fill_description(self):
        """Check for nested description under slot-fill '...' token."""
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if re.match(r'with\s+\w+\s*=\s*\.\.\.\s*$', stripped):
                # Check if next non-empty line is an indented description
                for j in range(i, min(i + 3, len(self.lines))):
                    next_line = self.lines[j].strip()
                    if next_line.startswith("description:"):
                        self.errors.append((i, "ERROR",
                            f"Slot-fill '...' has nested description (line {i}) — "
                            f"description is inherited from Level 1 definition; remove the nested block"))
                        break
                    if next_line and not next_line.startswith("#"):
                        break

    def _check_apex_target_shared_class(self):
        """Check apex:// targets: one @InvocableMethod per class → one class per action.

        Salesforce permits only one @InvocableMethod per Apex class. Two failure modes:
          1. apex://ClassName.methodName  — method-suffix form implies many methods on one class
          2. two apex:// targets resolving to the same class name — a shared class
        Both produce Apex that cannot compile/deploy/publish.
        """
        seen_classes: dict[str, int] = {}
        for i, line in enumerate(self.lines, 1):
            # Skip comment lines — a `# see apex://Foo.bar` note is not a real target.
            if line.lstrip().startswith("#"):
                continue
            match = re.search(r'apex://([A-Za-z0-9_.]+)', line)
            if not match:
                continue
            target = match.group(1)
            class_name = target.split(".", 1)[0]

            if "." in target:
                self.warnings.append((i, "WARN",
                    f"apex:// target '{target}' uses a method suffix (line {i}) — "
                    f"the target names the CLASS, not a method (use 'apex://{class_name}'). "
                    f"Salesforce allows only one @InvocableMethod per class, so each action "
                    f"needs its own class (e.g. 'apex://{class_name}{target.split('.', 1)[1][:1].upper()}{target.split('.', 1)[1][1:]}')."))

            if class_name in seen_classes:
                self.warnings.append((i, "WARN",
                    f"apex:// target class '{class_name}' is reused (line {i}, first seen line "
                    f"{seen_classes[class_name]}) — multiple actions cannot share one Apex class "
                    f"(only one @InvocableMethod per class). Give each action its own class."))
            else:
                seen_classes[class_name] = i

    def _check_redundant_routing_topic(self):
        """Check for redundant routing/menu topics that duplicate start_agent."""
        redundant_names = {"main_menu", "central_hub", "hub", "router", "routing",
                           "menu", "navigation", "dispatcher"}
        for i, line in enumerate(self.lines, 1):
            match = re.match(r'^topic\s+(\w+)\s*:', line)
            if match:
                topic_name = match.group(1).lower()
                if topic_name in redundant_names:
                    self.warnings.append((i, "WARN",
                        f"Topic '{match.group(1)}' looks like a redundant router (line {i}) — "
                        f"in router-first architecture, start_agent IS the router. "
                        f"Remove this topic and have subagents transition to @subagent.agent_router instead."))

    def _auto_resolve_placeholder(self):
        """Auto-resolve REPLACE_WITH_EINSTEIN_AGENT_USER placeholder."""
        if "REPLACE_WITH_EINSTEIN_AGENT_USER" not in self.content:
            return

        # Try to query org for Einstein Agent Users
        try:
            result = subprocess.run(
                ["sf", "data", "query", "--query",
                 "SELECT Username FROM User WHERE Profile.Name = 'Einstein Agent User' AND IsActive = true",
                 "--json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                records = data.get("result", {}).get("records", [])
                if records:
                    username = records[0]["Username"]
                    self.warnings.append((0, "INFO",
                        f"Found Einstein Agent User: {username} — "
                        f"replace REPLACE_WITH_EINSTEIN_AGENT_USER with this value"))
        except Exception:
            pass

        self.warnings.append((0, "WARN",
            "REPLACE_WITH_EINSTEIN_AGENT_USER placeholder found — "
            "set default_agent_user to a valid Einstein Agent User email"))


def main():
    """Main entry point for the PostToolUse hook."""
    input_data = read_stdin_safe(timeout_seconds=0.1)
    if not input_data:
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only validate Write/Edit on .agent files
    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".agent"):
        sys.exit(0)

    # Read the file content
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except (FileNotFoundError, IOError):
        sys.exit(0)

    # Run validation
    validator = AgentScriptValidator(file_path, content)
    result = validator.validate()

    # Format output
    messages = []
    for line_num, severity, msg in result["errors"]:
        messages.append(f"  ERROR: {msg}")
    for line_num, severity, msg in result["warnings"]:
        messages.append(f"  {severity}: {msg}")

    safety_note = (
        "\n\n  SAFETY: Run the safety review (Section 15 of /agentforce-generate) on this file "
        "for LLM-driven safety review (catches impersonation, dark patterns, proxy discrimination, "
        "euphemistic harm, manipulation, and other semantic risks that syntax checks cannot detect)."
    )

    if messages:
        context = "Agent Script Validation:\n" + "\n".join(messages) + safety_note
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": context,
            }
        }
        print(json.dumps(output))
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "Agent Script Validation: All syntax checks passed." + safety_note,
            }
        }
        print(json.dumps(output))


if __name__ == "__main__":
    main()
