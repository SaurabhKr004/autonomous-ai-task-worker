import os
import pytest
from agent.verifier import verify_task, generate_final_report, save_report
from agent.config import RUNS_DIR


def test_verifier_incomplete_status():
    result = verify_task(
        task="Upload invoice",
        final_status="max_steps",
        summary="Ran out of steps.",
        trace_steps=[],
        facts=[],
    )
    assert result["verified"] is False
    assert result["verdict"] == "FAILED"
    assert len(result["discrepancies"]) > 0


def test_generate_final_report_structure():
    verification = {
        "verified": True,
        "verdict": "VERIFIED",
        "evidence": ["Found invoice #101 in database", "Total $500 matches"],
        "discrepancies": [],
        "analysis": "Agent followed all instructions and produced valid proof.",
    }
    trace_steps = [
        {"step": 1, "type": "function_call", "tool": "read_file", "args": {"path": "inv.txt"}, "result": "Invoice 101"},
        {"step": 2, "type": "done", "summary": "Task complete"},
    ]
    report = generate_final_report(
        task="Verify invoice 101",
        status="done",
        summary="Found invoice #101.",
        trace_steps=trace_steps,
        facts=["Vendor: Acme"],
        verification=verification,
        elapsed_seconds=4.25,
    )
    assert "# Final Task Report" in report
    assert "✅ **VERIFIED**" in report
    assert "Found invoice #101 in database" in report
    assert "Vendor: Acme" in report
    assert "read_file" in report


def test_save_report_creates_file():
    report_text = "# Test Report\nEverything verified."
    path = save_report(report_text, "test_run_123")
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == report_text
    # Cleanup test artifact
    if os.path.exists(path):
        os.remove(path)
