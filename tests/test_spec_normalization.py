from __future__ import annotations

from agents.nodes import _normalize_spec
from utils.render import render_markdown
from utils.validators import validate_acceptance_coverage


def test_normalize_spec_coerces_story_and_structured_risks():
    spec = _normalize_spec(
        {
            "title": "One-click export",
            "type": "PRD",
            "definitions": {"Displayed Data": "Filtered data before pagination."},
            "user_stories": [
                {
                    "story": "As an Ops Analyst, I want to export data with a single click, so that I can analyze it.",
                    "acceptance_criteria": [
                        "Scenario: Successful export",
                        "Given I am an Ops Analyst",
                        "When I click Export",
                        "Then I receive a CSV",
                    ],
                }
            ],
            "risks": [
                {
                    "risk": "Large datasets may time out.",
                    "mitigation": "Set a row limit.",
                }
            ],
        },
        "PRD",
    )

    assert spec["user_stories"][0]["as_a"] == "Ops Analyst"
    assert spec["user_stories"][0]["i_want"] == "to export data with a single click"
    assert spec["user_stories"][0]["so_that"] == "I can analyze it"
    assert spec["glossary"] == {"Displayed Data": "Filtered data before pagination."}
    assert spec["risks"] == ["Large datasets may time out. Mitigation: Set a row limit."]


def test_split_gwt_acceptance_criteria_are_valid():
    findings = validate_acceptance_coverage(
        {
            "user_stories": [
                {
                    "acceptance_criteria": [
                        "Scenario: Successful export",
                        "Given I am an Ops Analyst",
                        "When I click Export",
                        "Then I receive a CSV",
                    ]
                }
            ]
        }
    )

    assert findings == []


def test_prd_render_formats_normalized_risks_without_dict_literals():
    markdown = render_markdown(
        _normalize_spec(
            {
                "title": "One-click export",
                "type": "PRD",
                "user_stories": [],
                "risks": [{"risk": "Large datasets may time out.", "mitigation": "Set a row limit."}],
            },
            "PRD",
        )
    )

    assert "{'risk'" not in markdown
    assert "Large datasets may time out. Mitigation: Set a row limit." in markdown


def test_normalize_spec_formats_dict_items_in_all_string_list_fields():
    spec = _normalize_spec(
        {
            "title": "One-click export",
            "type": "PRD",
            "objectives": [{"description": "Reduce support tickets."}],
            "functional_requirements": [{"id": "FR-1", "description": "Export data as CSV."}],
            "non_functional_requirements": [
                {"type": "Performance", "description": "Exports complete within 5 seconds."}
            ],
            "metrics": [{"name": "Ticket reduction", "target": "20%"}],
            "dependencies": [{"name": "Data API", "description": "Provides filtered records."}],
            "open_questions": [{"question": "Which reports are in scope?"}],
            "scope": {
                "in_scope": [{"description": "CSV export."}],
                "out_of_scope": [{"description": "PDF export."}],
            },
        },
        "PRD",
    )

    list_fields = (
        "objectives",
        "functional_requirements",
        "non_functional_requirements",
        "metrics",
        "dependencies",
        "open_questions",
    )
    values = [item for field in list_fields for item in spec[field]]
    values.extend(spec["scope"]["in_scope"])
    values.extend(spec["scope"]["out_of_scope"])

    assert all(isinstance(value, str) for value in values)
    assert all("{'" not in value for value in values)
    assert "Performance: Exports complete within 5 seconds." in spec["non_functional_requirements"]
    assert "FR-1: Export data as CSV." in spec["functional_requirements"]
    assert "Ticket reduction: target: 20%" in spec["metrics"]
