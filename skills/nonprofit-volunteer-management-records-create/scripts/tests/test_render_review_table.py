"""Tests for render-review-table.py — the fixed-column review table.

Run from the skill's scripts/tests directory:
    cd contributed-skills/npc-titan/nonprofit-volunteer-management-records-create/scripts/tests
    python3 -m unittest test_render_review_table

Covers: one column order for every row regardless of the order fields arrive in, label
headers, lookups last, required fields shown as needs-input, optional fields with no value
omitted, only reuse and needs-input tags printed, the Name column dropped when the row label shows it, same-on-every-row columns moved
above the table, identical-row grouping (and --expand), and the spec errors the agent can hit.
"""

import importlib.util
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "render-review-table.py")

_spec = importlib.util.spec_from_file_location("render_review_table", SCRIPT)
rrt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rrt)
GUIDE = rrt.parse_field_guide(rrt.DEFAULT_FIELD_GUIDE)


def f(value, origin="given"):
    return {"value": value, "origin": origin}


def render(spec, expand=False):
    return rrt.build_table(spec, GUIDE, expand=expand)


def run_cli(spec, *args):
    return subprocess.run([sys.executable, SCRIPT, *args], input=json.dumps(spec),
                          capture_output=True, text=True)


def header_row(table):
    return [line for line in table.splitlines() if line.startswith("| Record")][0]


def body_rows(table):
    lines = table.splitlines()
    start = lines.index(header_row(table)) + 2
    rows = []
    for line in lines[start:]:
        if not line.startswith("|"):
            break
        rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def headers(table):
    return [c.strip() for c in header_row(table).strip().strip("|").split("|")]


class FieldGuideParsing(unittest.TestCase):
    def test_every_creatable_entity_is_parsed(self):
        for entity in ("VolunteerInitiative", "Location", "Address", "OperatingHours",
                       "TimeSlot", "Position", "PositionQualification", "JobPosition",
                       "JobPositionQualification", "JobPositionShift", "Competency",
                       "Examination"):
            self.assertIn(entity, GUIDE, entity)
            self.assertTrue(GUIDE[entity], entity)

    def test_relationship_rows_map_to_api_names(self):
        apis = {fld["api"]: fld for fld in GUIDE["JobPosition"]}
        self.assertIn("VolunteerInitiativeId", apis)
        self.assertTrue(apis["VolunteerInitiativeId"]["lookup"])
        self.assertFalse(apis["Title"]["lookup"])
        self.assertTrue(apis["Title"]["schema_required"])


class MixedKeyOrder(unittest.TestCase):
    """The defect this script exists for: fields arriving in a different order per record."""

    def spec(self):
        return {"entity": "JobPositionShift", "records": [
            {"label": "Sat 3 Oct", "fields": {
                "JobPositionId": f("Greeter — Eastside", "reuse"),
                "StartDate": f("2026-10-03"), "EndDate": f("2026-10-03"),
                "StartTime": f("09:00"), "EndTime": f("12:00"),
                "TimeZone": f("America/Chicago", "default"),
                "Status": f("Upcoming", "default"), "MaximumAttendeesCount": f(8)}},
            {"label": "Sun 4 Oct", "fields": {
                "MaximumAttendeesCount": f(6), "Status": f("Draft"),
                "EndTime": f("16:00"), "TimeZone": f("America/Denver"),
                "StartTime": f("13:00"), "EndDate": f("2026-10-04"),
                "StartDate": f("2026-10-04"),
                "JobPositionId": f("Greeter — Westside", "reuse")}},
            {"label": "Sat 10 Oct", "fields": {
                "Status": f("Upcoming", "default"), "StartTime": f("09:00"),
                "JobPositionId": f("Greeter — Eastside", "reuse"),
                "TimeZone": f("America/Chicago", "default"), "EndDate": f("2026-10-10"),
                "MaximumAttendeesCount": f(8), "EndTime": f("12:00"),
                "StartDate": f("2026-10-10")}},
        ]}

    def test_every_value_lands_under_its_own_header(self):
        table = render(self.spec())
        cols = headers(table)
        rows = body_rows(table)
        self.assertEqual(len(rows), 3)
        expected = [
            {"Start Date": "2026-10-03", "Start Time": "09:00", "End Time": "12:00",
             "Maximum Attendees Count": "8", "Status": "Upcoming",
             "Time Zone": "America/Chicago", "Job Position": "Greeter — Eastside `reuse`"},
            {"Start Date": "2026-10-04", "Start Time": "13:00", "End Time": "16:00",
             "Maximum Attendees Count": "6", "Status": "Draft",
             "Time Zone": "America/Denver", "Job Position": "Greeter — Westside `reuse`"},
            {"Start Date": "2026-10-10", "Start Time": "09:00", "End Time": "12:00",
             "Maximum Attendees Count": "8", "Status": "Upcoming",
             "Time Zone": "America/Chicago", "Job Position": "Greeter — Eastside `reuse`"},
        ]
        for row, want in zip(rows, expected):
            cells = dict(zip(cols, row))
            for header, value in want.items():
                self.assertEqual(cells[header], value, header)

    def test_column_order_is_tier_order_then_lookups(self):
        cols = headers(render(self.spec()))
        self.assertEqual(cols, [
            "Record", "Start Date", "End Date", "Start Time", "End Time", "Time Zone",
            "Status", "Maximum Attendees Count", "Job Position"])

    def test_order_does_not_depend_on_the_first_record(self):
        spec = self.spec()
        reversed_spec = {"entity": spec["entity"], "records": list(reversed(spec["records"]))}
        self.assertEqual(headers(render(spec)), headers(render(reversed_spec)))

    def test_relationship_name_and_api_name_are_one_column(self):
        spec = {"entity": "JobPosition", "records": [
            {"fields": {"Name": f("A"), "Title": f("A"),
                        "VolunteerInitiative": f("Food Pantry", "reuse")}},
            {"fields": {"Name": f("B"), "Title": f("B"),
                        "VolunteerInitiativeId": f("Food Drive", "reuse")}},
        ]}
        cols = headers(render(spec))
        self.assertEqual(cols.count("Volunteer Initiative"), 1)
        self.assertEqual(cols[-1], "Volunteer Initiative")


class Headers(unittest.TestCase):
    def test_labels_not_api_names(self):
        spec = {"entity": "VolunteerInitiative", "records": [
            {"fields": {"Name": f("Child"), "ParentVolunteerInitiative":
                        f("Parent Program", "reuse")}}]}
        cols = headers(render(spec))
        self.assertIn("Parent Volunteer Initiative", cols)
        self.assertNotIn("ParentVolunteerInitiativeId", cols)

    def test_label_with_pipe_or_newline_keeps_the_table_shape(self):
        spec = {"entity": "JobPosition",
                "labels": {"VolunteerInitiativeId": "Related | Initiative\nName"},
                "records": [{"fields": {"Name": f("A"), "Title": f("A"),
                                        "VolunteerInitiativeId": f("P", "new")}}]}
        table = render(spec)
        self.assertIn("Related \\| Initiative Name", header_row(table))
        for line in table.splitlines():
            if line.startswith("| "):
                self.assertEqual(len(line.replace("\\|", "").split("|")),
                                 len(header_row(table).replace("\\|", "").split("|")))

    def test_shared_column_label_is_escaped(self):
        spec = {"entity": "JobPosition",
                "labels": {"VolunteerInitiativeId": "A | B"},
                "records": [{"fields": {"Name": f("A"), "Title": f("T"),
                                        "VolunteerInitiativeId": f("P", "new")}},
                            {"fields": {"Name": f("B"), "Title": f("U"),
                                        "VolunteerInitiativeId": f("P", "new")}}]}
        self.assertIn("A \\| B", render(spec))

    def test_describe_label_overrides(self):
        spec = {"entity": "JobPosition",
                "labels": {"VolunteerInitiativeId": "Related Volunteer Initiative"},
                "records": [{"fields": {"Name": f("A"), "Title": f("A"),
                                        "VolunteerInitiativeId": f("P", "new")}}]}
        self.assertIn("Related Volunteer Initiative", headers(render(spec)))

    def test_custom_fields_after_standard_before_lookups(self):
        spec = {"entity": "JobPosition", "records": [{"fields": {
            "Name": f("A"), "Title": f("A"), "Region__c": f("North"),
            "LocationId": f("Eastside Hall", "reuse")}}]}
        cols = headers(render(spec))
        self.assertEqual(cols, ["Record", "Title", "Region", "Location"])


class MissingFields(unittest.TestCase):
    def test_optional_field_with_no_value_is_omitted(self):
        spec = {"entity": "VolunteerInitiative", "records": [
            {"fields": {"Name": f("A"), "Status": f("Upcoming", "default")}},
            {"fields": {"Name": f("B"), "Status": f("Upcoming", "default")}}]}
        cols = headers(render(spec))
        self.assertNotIn("Start Date", cols)
        self.assertNotIn("Description", cols)

    def test_optional_field_set_on_one_row_shows_dash_elsewhere(self):
        spec = {"entity": "VolunteerInitiative", "records": [
            {"fields": {"Name": f("A"), "Description": f("Weekly pantry", "generated")}},
            {"fields": {"Name": f("B")}}]}
        table = render(spec)
        cells = dict(zip(headers(table), body_rows(table)[1]))
        self.assertEqual(cells["Description"], "—")

    def test_required_field_missing_shows_needs_input(self):
        spec = {"entity": "JobPosition", "records": [{"fields": {"Name": f("Greeter")}}]}
        table = render(spec)
        cells = dict(zip(headers(table), body_rows(table)[0]))
        self.assertEqual(cells["Title"], "`needs-input`")
        self.assertIn("Still needed before this can be written: Title (row 1)", table)

    def test_explicit_needs_input_origin(self):
        spec = {"entity": "Location", "records": [
            {"fields": {"Name": f("Eastside Hall"),
                        "LocationType": f(None, "needs-input")}},
            {"fields": {"Name": f("Westside Hall"),
                        "LocationType": f(None, "needs-input")}}]}
        table = render(spec)
        self.assertIn("Location Type (rows 1, 2)", table)

    def test_schema_required_blank_value_is_needs_input(self):
        spec = {"entity": "JobPosition", "records": [
            {"fields": {"Name": f("A"), "Title": f("", "given")}}]}
        self.assertIn("Title (row 1)", render(spec))

    def test_always_set_but_not_schema_required_can_be_left_blank(self):
        spec = {"entity": "Address", "records": [{"fields": {
            "ParentId": f("Eastside Hall", "new"), "LocationType": f("Business Site"),
            "Street": f("12 Main St"), "City": f("Austin"), "State": f("TX"),
            "PostalCode": f("78701"), "Country": f("", "given")}}]}
        table = render(spec)
        cells = dict(zip(headers(table), body_rows(table)[0]))
        self.assertEqual(cells["Country"], "—")
        self.assertNotIn("Still needed", table)

    def test_required_custom_field(self):
        spec = {"entity": "JobPosition", "requiredCustomFields": ["Region__c"],
                "records": [{"fields": {"Name": f("A"), "Title": f("A")}}]}
        table = render(spec)
        self.assertIn("Region", headers(table))
        self.assertIn("Region (row 1)", table)


class Grouping(unittest.TestCase):
    def spec(self):
        same = {"JobPositionId": f("Sorter", "reuse"), "StartDate": f("2026-10-03"),
                "EndDate": f("2026-10-03"), "StartTime": f("09:00"), "EndTime": f("12:00"),
                "TimeZone": f("America/Chicago", "default")}
        other = dict(same, StartTime=f("13:00"), EndTime=f("16:00"))
        return {"entity": "JobPositionShift", "records": [
            {"fields": dict(same)}, {"fields": dict(same)}, {"fields": dict(same)},
            {"fields": other}]}

    def test_identical_rows_collapse(self):
        rows = body_rows(render(self.spec()))
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[0][0].startswith("Rows 1–3"))
        self.assertIn('say "show all 3"', rows[0][0])
        self.assertEqual(rows[1][0], "4")

    def test_expand_lists_every_row(self):
        rows = body_rows(render(self.spec(), expand=True))
        self.assertEqual([r[0] for r in rows], ["1", "2", "3", "4"])

    def test_only_consecutive_rows_group(self):
        spec = self.spec()
        spec["records"] = [spec["records"][0], spec["records"][3], spec["records"][1]]
        self.assertEqual(len(body_rows(render(spec))), 3)

    def test_different_names_do_not_group(self):
        spec = {"entity": "Competency", "records": [
            {"fields": {"Name": f("Forklift")}}, {"fields": {"Name": f("First Aid")}}]}
        self.assertEqual(len(body_rows(render(spec))), 2)


class NameColumn(unittest.TestCase):
    def test_name_matching_label_is_not_repeated(self):
        spec = {"entity": "Position", "records": [
            {"fields": {"Name": f("Planter"), "Description": f("Plants trees", "generated")}},
            {"fields": {"Name": f("Site Lead", "generated"),
                        "Description": f("Leads the crew", "generated")}}]}
        table = render(spec)
        self.assertNotIn("Name", headers(table))
        self.assertEqual([r[0] for r in body_rows(table)],
                         ["1 · Planter", "2 · Site Lead"])

    def test_name_kept_when_a_label_differs(self):
        spec = {"entity": "Position", "records": [
            {"label": "Role A", "fields": {"Name": f("Planter")}},
            {"fields": {"Name": f("Site Lead")}}]}
        self.assertIn("Name", headers(render(spec)))

    def test_missing_name_keeps_the_column(self):
        spec = {"entity": "JobPosition", "records": [
            {"fields": {"Name": f(None, "needs-input"), "Title": f("A")}}]}
        table = render(spec)
        self.assertIn("Name", headers(table))
        self.assertIn("Name (row 1)", table)

    def test_same_fields_different_names_still_two_rows(self):
        spec = {"entity": "Position", "records": [
            {"fields": {"Name": f("Planter"), "Status": f("Upcoming", "default")}},
            {"fields": {"Name": f("Waterer"), "Status": f("Upcoming", "default")}}]}
        self.assertEqual(len(body_rows(render(spec))), 2)


class SharedColumns(unittest.TestCase):
    def spec(self):
        return {"entity": "JobPosition", "records": [
            {"fields": {"Name": f("Planter – LA"), "Title": f("Planter", "default"),
                        "Status": f("Upcoming", "default"),
                        "LocationId": f("Los Angeles", "new")}},
            {"fields": {"Name": f("Planter – NY"), "Title": f("Planter", "default"),
                        "Status": f("Upcoming", "default"),
                        "LocationId": f("New York", "new")}}]}

    def test_same_value_on_every_row_moves_above_the_table(self):
        table = render(self.spec())
        self.assertIn("Same on every row: Title Planter · Status Upcoming", table)
        self.assertEqual(headers(table), ["Record", "Location"])

    def test_a_single_row_keeps_every_column(self):
        spec = self.spec()
        spec["records"] = spec["records"][:1]
        table = render(spec)
        self.assertNotIn("Same on every row", table)
        self.assertIn("Status", headers(table))

    def test_needs_input_column_stays_in_the_table(self):
        spec = {"entity": "Location", "records": [
            {"fields": {"Name": f("A"), "LocationType": f(None, "needs-input")}},
            {"fields": {"Name": f("B"), "LocationType": f(None, "needs-input")}}]}
        table = render(spec)
        self.assertIn("Location Type", headers(table))
        self.assertNotIn("Same on every row", table)

    def test_rows_that_differ_only_in_shared_columns_still_group(self):
        spec = {"entity": "JobPositionShift", "records": [
            {"fields": {"JobPositionId": f("Sorter", "reuse"), "StartDate": f("2026-10-03"),
                        "StartTime": f("09:00")}}] * 3}
        rows = body_rows(render(spec))
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][0].startswith("Rows 1–3"))


class OriginTags(unittest.TestCase):
    def spec(self):
        return {"entity": "JobPosition", "records": [{"fields": {
            "Name": f("Planter – LA"), "Title": f("Planter", "default"),
            "Description": f("Plant trees", "generated"),
            "LocationId": f("Los Angeles", "new"),
            "VolunteerInitiativeId": f("Tree Planting – LA", "reuse")}}]}

    def test_only_reuse_is_tagged(self):
        table = render(self.spec())
        cells = dict(zip(headers(table), body_rows(table)[0]))
        self.assertEqual(cells["Title"], "Planter")
        self.assertEqual(cells["Description"], "Plant trees")
        self.assertEqual(cells["Location"], "Los Angeles")
        self.assertEqual(cells["Volunteer Initiative"], "Tree Planting – LA `reuse`")
        for tag in ("`given`", "`default`", "`generated`", "`new`"):
            self.assertNotIn(tag, table)

    def test_reuse_note_only_when_a_cell_is_reused(self):
        self.assertIn("`reuse` = links to a record already in your org", render(self.spec()))
        spec = self.spec()
        spec["records"][0]["fields"]["VolunteerInitiativeId"] = f("Tree Planting – LA", "new")
        self.assertNotIn("`reuse` =", render(spec))

    def test_needs_input_note_when_something_is_missing(self):
        spec = {"entity": "JobPosition", "records": [{"fields": {"Name": f("Greeter")}}]}
        self.assertIn("`needs-input` = required, still missing", render(spec))


class Title(unittest.TestCase):
    def test_default_title_counts_rows(self):
        spec = {"entity": "Competency", "records": [
            {"fields": {"Name": f("A")}}, {"fields": {"Name": f("B")}}]}
        self.assertTrue(render(spec).startswith("Records to insert — 2 Competencies"))

    def test_series_title_override(self):
        spec = {"entity": "JobPositionShift",
                "title": "Records to insert — 12 Job Position Shifts (1 series)",
                "records": [{"label": "Saturdays 9:00–12:00", "fields": {
                    "JobPositionId": f("Driver", "new"),
                    "StartDate": f("every Saturday from 3 Oct 2026"),
                    "EndDate": f("same day"), "StartTime": f("09:00"), "EndTime": f("12:00"),
                    "TimeZone": f("America/Chicago", "default")}}]}
        table = render(spec)
        self.assertTrue(table.startswith("Records to insert — 12 Job Position Shifts (1 series)"))
        self.assertNotIn("Still needed", table)


class Errors(unittest.TestCase):
    def assert_fails(self, spec, fragment):
        result = run_cli(spec)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(fragment, result.stderr)

    def test_unknown_entity(self):
        self.assert_fails({"entity": "JobPositionAssignment",
                           "records": [{"fields": {"Name": f("x")}}]}, "unknown entity")

    def test_undocumented_field(self):
        self.assert_fails({"entity": "Position", "records": [
            {"fields": {"Name": f("x"), "Category": f("y")}}]}, "not in field-guide.md")

    def test_system_managed_field(self):
        self.assert_fails({"entity": "JobPositionShift", "records": [
            {"fields": {"RemainingCapacity": f(3)}}]}, "system-managed")

    def test_bad_origin(self):
        self.assert_fails({"entity": "Competency", "records": [
            {"fields": {"Name": f("x", "seeded")}}]}, "origin")

    def test_lookup_needs_reuse_or_new(self):
        self.assert_fails({"entity": "JobPosition", "records": [{"fields": {
            "Name": f("x"), "Title": f("x"), "LocationId": f("Hall", "given")}}]},
            "is a lookup")

    def test_lookup_shows_name_not_id(self):
        self.assert_fails({"entity": "JobPosition", "records": [{"fields": {
            "Name": f("x"), "Title": f("x"),
            "LocationId": f("131Hs000000Abc1IAC", "reuse")}}]}, "looks like a record Id")

    def test_empty_records(self):
        self.assert_fails({"entity": "Competency", "records": []}, "non-empty list")

    def test_cli_happy_path(self):
        result = run_cli({"entity": "Competency", "records": [
            {"fields": {"Name": f("Forklift Operation")}}]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Records to insert — 1 Competency", result.stdout)
        self.assertIn("| 1 · Forklift Operation |", result.stdout)


if __name__ == "__main__":
    unittest.main()
