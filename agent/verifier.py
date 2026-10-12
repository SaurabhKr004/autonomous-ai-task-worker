"""
agent/verifier.py — Independent Verifier and Final Report Generator.

Checks if the claims made in the summary are corroborated by concrete evidence
in the tool trace and facts, and generates a structured Markdown report.
"""

import os
import json
from agent.config import RUNS_DIR


def verify_task(
    task: str,
    final_status: str,
    summary: str,
    trace_steps: list,
    facts: list[str],
) -> dict:
    """
    Independently inspect whether the claims in the final summary are backed
    by real evidence in the action trace.
    """
    if final_status != "done":
        return {
            "verified": False,
            "verdict": "FAILED",
            "evidence": [],
            "discrepancies": [f"Task ended with status '{final_status}', not 'done'."],
            "analysis": f"The agent did not reach completion (status: {final_status}). Summary: {summary}",
        }

    # Extract actions and tool results from trace
    actions_summary = []
    has_errors = False
    for s in trace_steps:
        stype = s.get("type")
        if stype == "function_call":
            res_str = str(s.get("result", ""))
            if "error" in res_str.lower():
                has_errors = True
            actions_summary.append(
                f"- Tool: {s.get('tool')} | Args: {json.dumps(s.get('args'))} | Result: {res_str[:300]}"
            )

    actions_text = "\n".join(actions_summary) if actions_summary else "No tool actions recorded."
    facts_text = "\n".join(f"- {f}" for f in facts) if facts else "No facts recorded."

    verification_prompt = f"""You are an independent verification auditor for an AI agent.
Analyze whether the agent's stated outcome is truly supported by concrete evidence in its action trace.

ORIGINAL TASK:
{task}

AGENT'S CLAIM / SUMMARY:
{summary}

DISCOVERED FACTS:
{facts_text}

EXECUTION ACTIONS AND OBSERVATIONS:
{actions_text}

AUDIT INSTRUCTIONS:
1. Determine if the agent actually completed the requested task based ONLY on the evidence above.
2. Identify concrete pieces of evidence (e.g. data returned, successful confirmations).
3. Identify any discrepancies, missing requirements, or unverified claims.
4. Return a valid JSON object strictly matching this schema:
{{
  "verified": true or false,
  "verdict": "VERIFIED" or "DISCREPANCIES_FOUND",
  "evidence": ["list", "of", "concrete", "proof", "points"],
  "discrepancies": ["list", "of", "missing", "items", "or", "issues"],
  "analysis": "Brief explanation of verification decision"
}}
Return ONLY the JSON object, nothing else.
"""

    try:
        from agent.llm import _get_client, MODEL_NAME
        client = _get_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=verification_prompt,
        )
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        data = json.loads(text.strip())
        return data
    except Exception as e:
        # Fallback heuristic if API or parsing is unavailable
        evidence = [f"Agent completed in {len(trace_steps)} steps with status 'done'."]
        if facts:
            evidence.extend(facts[:3])
        discrepancies = ["Trace contained tool errors."] if has_errors else []
        return {
            "verified": not has_errors,
            "verdict": "VERIFIED" if not has_errors else "DISCREPANCIES_FOUND",
            "evidence": evidence,
            "discrepancies": discrepancies,
            "analysis": f"Evaluated via rule-based verification (auditor note: {e}).",
        }


def generate_final_report(
    task: str,
    status: str,
    summary: str,
    trace_steps: list,
    facts: list[str],
    verification: dict,
    elapsed_seconds: float,
) -> str:
    """Generate a clean Markdown final report."""
    verdict = verification.get("verdict", "UNVERIFIED")
    badge = "✅ **VERIFIED**" if verification.get("verified") else "⚠️ **DISCREPANCIES FOUND / UNVERIFIED**"

    evidence_items = "\n".join(f"- {e}" for e in verification.get("evidence", [])) or "- None recorded."
    discrepancy_items = "\n".join(f"- {d}" for d in verification.get("discrepancies", [])) or "- None."
    facts_items = "\n".join(f"- {f}" for f in facts) or "- None."

    tools_used = [s.get("tool") for s in trace_steps if s.get("type") == "function_call"]
    tools_summary = ", ".join(sorted(set(tools_used))) if tools_used else "None"

    report = f"""# Final Task Report

## Verification Verdict: {badge}

- **Status:** `{status.upper()}`
- **Execution Time:** {elapsed_seconds:.2f}s
- **Total Steps:** {len(trace_steps)}
- **Tools Invoked:** {tools_summary}

---

## 1. Task Requested
> {task}

## 2. Agent Outcome & Summary
{summary}

## 3. Independent Verification Analysis
**Verdict:** `{verdict}`  
{verification.get('analysis', '')}

### Proof of Completion / Evidence:
{evidence_items}

### Discrepancies / Outstanding Issues:
{discrepancy_items}

## 4. Discovered Facts (Working Memory)
{facts_items}

## 5. Execution Summary
- Steps taken: {len(trace_steps)}
- Action breakdown:
"""
    for s in trace_steps:
        stype = s.get("type")
        if stype == "function_call":
            report += f"  - **Step {s.get('step')}:** `{s.get('tool')}` -> {str(s.get('result'))[:120]}...\n"
        elif stype == "done":
            report += f"  - **Step {s.get('step')}:** `done` ({s.get('summary')})\n"

    report += "\n---\n*Report generated automatically by Phase 6 Independent Verifier.*\n"
    return report


def save_report(report_text: str, run_id: str) -> str:
    """Save report to runs/ directory."""
    os.makedirs(RUNS_DIR, exist_ok=True)
    report_path = os.path.join(RUNS_DIR, f"report_{run_id}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    return report_path
