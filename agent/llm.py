"""
llm.py — Gemini API wrapper.

Handles all communication with the Gemini 2.0 Flash model.
The rest of the code never calls the API directly — it goes through here.

Key responsibility: send messages + tool definitions, get back the raw
response so we can preserve thought_signatures that Gemini requires
for function-calling round-trips.
"""

import os
from google import genai
from google.genai import types
from agent.config import MODEL_NAME


def _get_client() -> genai.Client:
    """
    Create a Gemini client using the API key from the .env file.
    The key is loaded by main.py via dotenv before this is called.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Make sure it's set in your .env file."
        )
    return genai.Client(api_key=api_key)


# ---- The system prompt for the agent ----
SYSTEM_PROMPT = """\
You are an autonomous AI task worker. The user gives you a task in plain
English, and you complete it by calling tools step by step.

Rules:
1. Think about what to do, then call exactly ONE tool per step.
2. After each tool result, decide your next action.
3. Save important facts you discover (call save_fact tool).
4. If something fails, try an alternative approach or ask the user.
5. When the task is fully complete, call the "done" tool with a summary
   and the evidence that the task succeeded.
6. NEVER claim the task is done unless you have verified the result.
7. If you are unsure or need clarification, call the "ask_user" tool.
8. Keep your reasoning concise.
"""


def chat(
    messages: list,
    tool_declarations: list[dict],
    system_instruction: str | None = None,
) -> dict:
    """
    Send a conversation to Gemini and get the response.

    Args:
        messages: List of conversation Content objects (or dicts).
                  We pass these directly to the API to preserve
                  thought_signatures from previous model turns.
        tool_declarations: List of tool schemas in Gemini function-calling
                           format (will be wrapped into Tool objects).

    Returns:
        A dict with:
          - "type": "text" or "function_call"
          - "content": text string (if type is "text")
          - "name": tool name (if type is "function_call")
          - "args": tool args dict (if type is "function_call")
          - "raw_content": the raw Content object from the model response.
              This MUST be appended to the messages list to preserve
              thought_signatures for future turns.
    """
    client = _get_client()

    # Build the tools config for Gemini.
    tools = None
    if tool_declarations:
        tools = types.Tool(function_declarations=tool_declarations)

    # Make the API call.
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=messages,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction or SYSTEM_PROMPT,
            tools=[tools] if tools else None,
        ),
    )

    # ---- Parse the response ----
    candidate = response.candidates[0]
    raw_content = candidate.content  # Preserve this for round-trips!

    # Look through parts to find a function call or text.
    function_call_part = None
    text_parts = []

    for part in raw_content.parts:
        if part.function_call:
            function_call_part = part
        elif part.text:
            text_parts.append(part.text)

    # If the model wants to call a function, return that.
    if function_call_part:
        fc = function_call_part.function_call
        args = dict(fc.args) if fc.args else {}
        return {
            "type": "function_call",
            "name": fc.name,
            "args": args,
            "raw_content": raw_content,
        }

    # Otherwise it's a text response.
    combined_text = "\n".join(text_parts) if text_parts else ""
    return {
        "type": "text",
        "content": combined_text,
        "raw_content": raw_content,
    }


def generate_plan(task: str, tool_names: list[str]) -> str:
    """
    Generate an initial rough step-by-step plan for the given task.
    """
    client = _get_client()
    prompt = (
        f"You are an autonomous AI planner. Create a concise, 3-5 step plan to complete this task:\n"
        f"Task: {task}\n\n"
        f"Available tools: {', '.join(tool_names)}\n\n"
        f"List only numbered steps. Keep it direct and actionable."
    )
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        return response.text.strip() if response.text else "1. Inspect tools.\n2. Execute actions.\n3. Verify."
    except Exception as e:
        return f"1. Inspect available tools ({', '.join(tool_names)}).\n2. Execute task steps sequentially.\n3. Verify completion."

