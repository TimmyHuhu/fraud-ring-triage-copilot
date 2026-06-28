from agents.report_writer import (
    build_case_report,
    build_case_report_html,
    run_report_writer,
)


def _sample_case():
    return {
        "case_id": "CASE-12345",
        "risk_score": 90,
        "risk_tier": "High",
        "priority": "P1",
        "recommended_action": "Escalate immediately",
        "pattern": "circular_flow",
        "evidence": "A → B → C → A",
        "accounts": ["A", "B", "C"],
        "reasons": ["Circular fund flow detected."],
        "action_rationale": "High-risk case.",
        "source_finding": {"pattern": "circular_flow"},
    }


def test_build_case_report_contains_key_fields():
    report = build_case_report(_sample_case())
    assert "CASE-12345" in report
    assert "Risk Score:** 90" in report
    assert "Escalate immediately" in report


def test_build_case_report_html_escapes_untrusted_values():
    case = _sample_case()
    case["accounts"] = ["<script>alert(1)</script>"]
    html_report = build_case_report_html(case)
    assert "<script>alert(1)</script>" not in html_report
    assert "&lt;script&gt;" in html_report


def test_run_report_writer_builds_one_report_per_case():
    cases = [_sample_case(), {**_sample_case(), "case_id": "CASE-99999"}]
    result = run_report_writer(cases)
    assert result["num_reports"] == 2
    assert result["reports"][0]["report_filename"].endswith(".html")
