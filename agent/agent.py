"""
agent.py — The core agent loop.

This is the heart of the system. It:
  1. Takes a user task (plain English).
  2. Sends it to the LLM along with available tools.
  3. When the LLM asks to call a tool, runs it and feeds back the result.
  4. Repeats until the LLM says "done" or the step limit is hit.
  5. Saves a JSON trace of every step to the /runs directory.

IMPORTANT: This file is completely task-agnostic.
It knows nothing about invoices, browsers, or any specific domain.
All domain knowledge lives in the tools and the system prompt.
"""

import json
import time
import os
from datetime import datetime, timezone

from google.genai import types

from agent.config import (
    MAX_STEPS, TIME_BUDGET_SECONDS, RUNS_DIR,
    MAX_RETRIES_PER_ACTION, LOOP_DETECTION_THRESHOLD
)
from agent.memory import Memory
from agent.llm import chat, generate_plan, SYSTEM_PROMPT
from tools.registry import ToolRegistry


def run_agent(
    task: str,
    registry: ToolRegistry,
    user_input_callback=None,
    step_callback=None,
) -> dict:
    """
    Execute the full agent loop for a given task.

    Args:
        task: The user's natural language request.
        registry: A ToolRegistry with all available tools registered.

    Returns:
        A dict with the final result:
          {"status": "done" | "max_steps" | "timeout" | "error",
           "summary": "...",
           "memory": {...},
           "steps": [...]}
    """
    # ---- Setup ----
    memory = Memory(task)
    start_time = time.time()
    trace_steps = []  # Every step recorded for the JSON trace.

    # Reliability tracking
    consecutive_action_key = None
    consecutive_action_count = 0
    action_consecutive_errors = {}

    # Build the initial conversation.
    # We start with a single user message containing the task.
    messages = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"Task: {task}\n\nDecide what to do first.")],
        )
    ]

    # Get the tool declarations to send to the LLM.
    tool_declarations = registry.get_all_declarations()

    print(f"\n{'='*60}")
    print(f"AGENT START -- Task: {task}")
    print(f"Available tools: {registry.list_names()}")
    print(f"Max steps: {MAX_STEPS} | Time budget: {TIME_BUDGET_SECONDS}s")
    print(f"{'='*60}\n")

    # ---- Phase 4: Initial Plan Generation ----
    print("[PLANNER] Creating initial plan...")
    initial_plan = generate_plan(task, registry.list_names())
    memory.set_plan(initial_plan)
    print(f"[PLANNER] Plan:\n{initial_plan}\n")

    final_status = "max_steps"  # Default if we exhaust all steps.
    final_summary = ""

    # ---- Main loop ----
    for step_num in range(1, MAX_STEPS + 1):
        # Check time budget.
        elapsed = time.time() - start_time
        if elapsed > TIME_BUDGET_SECONDS:
            final_status = "timeout"
            final_summary = f"Stopped: time budget exceeded ({elapsed:.0f}s)."
            print(f"\n[TIMEOUT] after {elapsed:.0f}s")
            break

        print(f"--- Step {step_num}/{MAX_STEPS} ---")

        # Ask the LLM what to do next with current working memory injected.
        current_system_prompt = f"{SYSTEM_PROMPT}\n\n# Working Memory\n{memory.to_prompt_string()}"
        try:
            response = chat(messages, tool_declarations, system_instruction=current_system_prompt)
        except Exception as e:
            # API errors should not crash the agent.
            error_msg = f"LLM API error: {e}"
            print(f"[ERROR] {error_msg}")
            trace_steps.append({"step": step_num, "error": error_msg})
            final_status = "error"
            final_summary = error_msg
            break

        # ---- CRITICAL: Append the raw model content to messages ----
        # This preserves thought_signatures that Gemini requires
        # for function-calling round-trips. Without this, the next
        # API call would fail with a 400 error.
        raw_content = response["raw_content"]
        messages.append(raw_content)

        # ---- Handle the LLM's response ----
        if response["type"] == "text":
            # The model sent a text message (not a tool call).
            text = response["content"]
            print(f"[LLM] {text[:200]}")

            trace_steps.append({
                "step": step_num,
                "type": "text",
                "content": text,
            })

            # Ask the LLM to continue (it may have just been thinking aloud).
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(
                        text="Continue. Call a tool for your next action, "
                             "or call 'done' if the task is complete."
                    )],
                )
            )
            continue

        # The model wants to call a tool.
        tool_name = response["name"]
        tool_args = response["args"]
        print(f"[TOOL] {tool_name}({json.dumps(tool_args, indent=2)})")

        # ---- Reliability: Loop Detection ----
        action_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
        if action_key == consecutive_action_key:
            consecutive_action_count += 1
        else:
            consecutive_action_key = action_key
            consecutive_action_count = 1

        if consecutive_action_count >= LOOP_DETECTION_THRESHOLD and tool_name not in ("done", "ask_user"):
            intervention_msg = (
                f"Loop detected: You have called '{tool_name}' with identical arguments "
                f"{consecutive_action_count} times consecutively without forward progress. "
                f"You MUST choose a different action, alter your arguments, or call 'ask_user' for help."
            )
            print(f"[LOOP DETECTED] {intervention_msg}")
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_name,
                        response={"result": intervention_msg},
                    )],
                )
            )
            trace_steps.append({
                "step": step_num,
                "type": "function_call",
                "tool": tool_name,
                "args": tool_args,
                "result": intervention_msg,
                "loop_detected": True,
            })
            if step_callback:
                step_callback(trace_steps[-1])
            continue

        # ---- Check for the special "done" tool ----
        if tool_name == "done":
            final_status = "done"
            final_summary = tool_args.get("summary", "Task completed.")
            print(f"\n[DONE] {final_summary}")
            trace_steps.append({
                "step": step_num,
                "type": "done",
                "summary": final_summary,
            })
            if step_callback:
                step_callback(trace_steps[-1])
            break

        # ---- Check for the special "ask_user" tool ----
        if tool_name == "ask_user":
            question = tool_args.get("question", "")
            print(f"\n[ASK USER] {question}")
            if user_input_callback:
                user_response = user_input_callback(question)
            else:
                user_response = input("Your answer: ")
            observation = f"User response: {user_response}"
            print(f"[USER ANSWER] {user_response}\n")

            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_name,
                        response={"result": observation},
                    )],
                )
            )
            trace_steps.append({
                "step": step_num,
                "type": "function_call",
                "tool": tool_name,
                "args": tool_args,
                "result": observation,
            })
            if step_callback:
                step_callback(trace_steps[-1])
            continue

        # ---- Check for the special "save_fact" tool ----
        if tool_name == "save_fact":
            fact = tool_args.get("fact", "")
            memory.add_fact(fact)
            print(f"[FACT] Saved: {fact}")
            observation = f"Fact saved: {fact}"

            # Send the function response back using proper types.
            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_name,
                        response={"result": observation},
                    )],
                )
            )
            trace_steps.append({
                "step": step_num,
                "type": "function_call",
                "tool": tool_name,
                "args": tool_args,
                "result": observation,
            })
            continue

        # ---- Check for the special "update_plan" tool ----
        if tool_name == "update_plan":
            plan_text = tool_args.get("plan", "")
            memory.set_plan(plan_text)
            print(f"[PLAN] Updated:\n{plan_text}")
            observation = f"Plan updated."

            messages.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_name,
                        response={"result": observation},
                    )],
                )
            )
            trace_steps.append({
                "step": step_num,
                "type": "function_call",
                "tool": tool_name,
                "args": tool_args,
                "result": observation,
            })
            continue

        # ---- Execute the tool ----
        prior_errors = action_consecutive_errors.get(tool_name, 0)
        if prior_errors >= MAX_RETRIES_PER_ACTION:
            observation = (
                f"Error: Action '{tool_name}' has failed {prior_errors} times consecutively. "
                f"Retry limit ({MAX_RETRIES_PER_ACTION}) exceeded. "
                f"Try an alternative tool or call 'ask_user' for assistance."
            )
            print(f"[RETRY LIMIT] {observation}")
        else:
            func = registry.get_func(tool_name)
            if func is None:
                observation = f"Error: Unknown tool '{tool_name}'. Available tools: {registry.list_names()}"
                print(f"[ERROR] {observation}")
            else:
                try:
                    observation = func(tool_args)
                except Exception as e:
                    # Tool errors are returned to the LLM, never raised.
                    observation = f"Error running {tool_name}: {e}"
                    print(f"[ERROR] {observation}")

        # Update failure tracking
        if str(observation).lower().startswith("error"):
            action_consecutive_errors[tool_name] = action_consecutive_errors.get(tool_name, 0) + 1
        else:
            action_consecutive_errors[tool_name] = 0

        # Show a preview of the result.
        preview = str(observation)[:300]
        print(f"[RESULT] {preview}")

        # Record it in memory.
        memory.record_action(tool_name, tool_args, str(observation))

        # ---- Feed the result back to the LLM ----
        # Use proper types to build the function response.
        messages.append(
            types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name=tool_name,
                    response={"result": str(observation)},
                )],
            )
        )

        # Log the step.
        trace_steps.append({
            "step": step_num,
            "type": "function_call",
            "tool": tool_name,
            "args": tool_args,
            "result": str(observation)[:2000],  # Truncate for trace.
        })
        if step_callback:
            step_callback(trace_steps[-1])

    # ---- Wrap up ----
    elapsed = time.time() - start_time

    # ---- Phase 6: Independent Verification & Final Report ----
    from agent.verifier import verify_task, generate_final_report, save_report

    print("\n" + "="*60)
    print("[VERIFIER] Performing independent verification of task completion...")
    verification = verify_task(
        task=task,
        final_status=final_status,
        summary=final_summary,
        trace_steps=trace_steps,
        facts=memory.facts,
    )
    print(f"[VERIFIER] Verdict: {verification.get('verdict')} (Verified: {verification.get('verified')})")
    print(f"[VERIFIER] Analysis: {verification.get('analysis')}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_text = generate_final_report(
        task=task,
        status=final_status,
        summary=final_summary,
        trace_steps=trace_steps,
        facts=memory.facts,
        verification=verification,
        elapsed_seconds=elapsed,
    )
    report_path = save_report(report_text, timestamp)
    print(f"[REPORT] Saved final report: {report_path}")

    result = {
        "status": final_status,
        "summary": final_summary,
        "task": task,
        "steps_taken": len(trace_steps),
        "elapsed_seconds": round(elapsed, 1),
        "memory": memory.to_dict(),
        "verification": verification,
        "report_path": report_path,
        "report_text": report_text,
        "steps": trace_steps,
    }

    # Save the JSON trace.
    _save_trace(result, timestamp=timestamp)

    print(f"\n{'='*60}")
    print(f"AGENT FINISHED -- Status: {final_status}")
    print(f"Steps: {len(trace_steps)} | Time: {elapsed:.1f}s")
    print(f"{'='*60}\n")

    return result


def _save_trace(result: dict, timestamp: str = None):
    """Save the full run trace as a JSON file in the /runs directory."""
    os.makedirs(RUNS_DIR, exist_ok=True)

    if not timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"run_{timestamp}.json"
    filepath = os.path.join(RUNS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    print(f"[TRACE] Saved: {filepath}")


# ---- Built-in tool declarations ----
# These are "virtual" tools handled directly by the agent loop,
# not by external functions.

DONE_DECLARATION = {
    "name": "done",
    "description": (
        "Call this when the task is fully complete. Provide a summary "
        "of what was accomplished and any evidence of completion."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "A concise summary of what was done and the outcome.",
            },
        },
        "required": ["summary"],
    },
}

SAVE_FACT_DECLARATION = {
    "name": "save_fact",
    "description": (
        "Save an important fact discovered during the task. "
        "Use this to remember key information (e.g. a vendor name, "
        "an amount, a date) for later steps."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "The fact to remember, as a short sentence.",
            },
        },
        "required": ["fact"],
    },
}

UPDATE_PLAN_DECLARATION = {
    "name": "update_plan",
    "description": (
        "Update or revise your current plan for completing the task. "
        "Use this if new information changes your approach, or to mark progress."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "plan": {
                "type": "string",
                "description": "The revised step-by-step plan.",
            },
        },
        "required": ["plan"],
    },
}

ASK_USER_DECLARATION = {
    "name": "ask_user",
    "description": (
        "Ask the human user a question or request confirmation/clarification. "
        "Use this when information is missing, ambiguous, or before risky/irreversible actions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The specific question or clarification needed from the human.",
            },
        },
        "required": ["question"],
    },
}
