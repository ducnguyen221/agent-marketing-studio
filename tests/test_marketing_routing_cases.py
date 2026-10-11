# -*- coding: utf-8 -*-
"""Structural checks for the locked, synthetic routing evaluation cases."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "tests" / "fixtures" / "marketing_routing_cases.yaml"
PHASES = ("A0", "A1", "B", "C")
EXPECTED_FIELDS = {
    "primary", "alternatives", "supports", "references_required",
    "references_forbidden", "ask", "allowed", "forbidden", "limitation",
}
ENTRYPOINTS = {"router", "marketing-director", "growth-analyst", "content-strategist",
               "campaign-strategist", "workflow-01", "workflow-02", "workflow-06",
               "workflow-07"}
PLANNED_REFERENCES = {
    "knowledge/playbooks/CONTENT_STRATEGY.md", "knowledge/playbooks/CRO_PLAYBOOK.md",
    "knowledge/playbooks/CUSTOMER_RESEARCH.md", "knowledge/playbooks/LEAD_GENERATION.md",
    "knowledge/playbooks/MEASUREMENT_PLAYBOOK.md", "knowledge/playbooks/OFFER_DESIGN.md",
}
PHASE_ROUTES = {
    "A0": {"marketing-routing", "campaign-pipeline", "content-production", "hook-writer",
           "thread-writer", "campaign-strategist", "content-strategist", "growth-analyst"},
    "A1": {"marketing-routing", "campaign-pipeline", "content-production", "hook-writer",
           "thread-writer", "growth-analyst", "content-strategist", "content-strategy", "customer-research", "direct-consultation"},
    "B": {"marketing-routing", "campaign-pipeline", "content-production", "hook-writer",
          "thread-writer", "growth-analyst", "content-strategist", "content-strategy", "customer-research", "offer-design", "lead-generation", "direct-consultation",
          "conversion-optimization"},
    "C": {"marketing-routing", "campaign-pipeline", "content-production", "hook-writer",
          "thread-writer", "growth-analyst", "content-strategist", "content-strategy", "customer-research", "offer-design", "lead-generation", "marketing-measurement", "direct-consultation",
          "conversion-optimization"},
}


def _cases_file() -> dict:
    return yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))


def test_fixture_locks_all_24_cases_and_each_phase_oracle():
    document = _cases_file()
    assert document["schema"] == 1
    assert tuple(document["phases"]) == PHASES
    cases = document["cases"]
    assert [case["id"] for case in cases] == [f"{number:02}" for number in range(1, 25)]

    for case in cases:
        scenarios = [{"id": "default", **case}, *case.get("scenario_variants", [])]
        scenario_ids = [scenario["id"] for scenario in scenarios]
        assert len(scenario_ids) == len(set(scenario_ids)), case["id"]
        for scenario in scenarios:
            assert scenario["prompt"].strip()
            assert isinstance(scenario["context"], dict)
            refs = scenario["context"].get("payload_refs", [])
            assert all(ref in document["payloads"] for ref in refs)
            assert tuple(scenario["expected_by_phase"]) == PHASES
            for phase, expectation in scenario["expected_by_phase"].items():
                assert set(expectation) == EXPECTED_FIELDS
                assert expectation["primary"] in PHASE_ROUTES[phase]
                assert set(expectation["alternatives"]) <= PHASE_ROUTES[phase]
                assert set(expectation["supports"]) <= PHASE_ROUTES[phase]
                assert not (set(expectation["references_required"]) & set(expectation["references_forbidden"]))
                for reference in expectation["references_required"]:
                    path = ROOT / reference
                    if phase == "A0":
                        assert path.is_file(), f"A0 ref missing: {reference}"
                    else:
                        assert path.is_file() or reference in PLANNED_REFERENCES
                for field in EXPECTED_FIELDS - {"primary", "limitation"}:
                    assert isinstance(expectation[field], list), f"{case['id']}:{field}"
        assert case["entrypoint_variants"]
        assert len(case["entrypoint_variants"]) == len(set(case["entrypoint_variants"]))
        assert set(case["entrypoint_variants"]) <= ENTRYPOINTS


def test_rubric_covers_routing_quality_and_authority_without_claiming_model_results():
    rubric = _cases_file()["rubric"]
    dimensions = {item["id"] for item in rubric["dimensions"]}
    assert dimensions == {"route", "clarify", "context", "output", "authority"}
    assert "All five dimensions pass" in rubric["scoring"]["pass"]
    assert "critical" in rubric["scoring"]
    sc6 = rubric["sc6_quality"]
    assert {item["id"] for item in sc6["dimensions"]} == {"insight", "topic", "draft", "editing"}
    assert set(sc6["scoring"]) == {0, 1, 2}
    assert "all four dimensions score 2" in sc6["acceptance"].lower()


def test_critical_cases_match_the_locked_plan():
    critical = {case["id"] for case in _cases_file()["cases"] if case["critical"]}
    assert critical == {"01", "03", "09", "17", "18", "19", "22"}


def test_eval_references_are_relative_repo_paths():
    for case in _cases_file()["cases"]:
        scenarios = [case, *case.get("scenario_variants", [])]
        for scenario in scenarios:
          for phase in PHASES:
            expectation = scenario["expected_by_phase"][phase]
            for field in ("references_required", "references_forbidden"):
                for reference in expectation[field]:
                    path = Path(reference)
                    assert not path.is_absolute()
                    assert ".." not in path.parts


def test_critical_set_and_mode_regressions_are_locked():
    cases = {case["id"]: case for case in _cases_file()["cases"]}
    linked = cases["06"]["scenario_variants"][0]
    assert linked["id"] == "campaign_linked_standalone_edit"
    for expectation in linked["expected_by_phase"].values():
        assert expectation["primary"] in {"campaign-pipeline", "marketing-routing"}
        assert "bypass_g1" in expectation["forbidden"]
    consult = cases["18"]["expected_by_phase"]
    execute = cases["18"]["scenario_variants"][0]
    assert cases["18"]["context"]["stage"] == "pre_publish_consult"
    assert execute["context"]["stage"] == "post_publish_execute"
    assert execute["context"]["actuals"] == "absent"
    assert "write_zero_data" in execute["expected_by_phase"]["C"]["forbidden"]
    assert not (set(linked["expected_by_phase"]["A0"]["supports"]) & {"offer-design", "lead-generation", "marketing-measurement"})
