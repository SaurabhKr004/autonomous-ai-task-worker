# Architecture Notes (Autonomous AI Task Worker)

## Goal
An agent that takes a natural language task, works out the steps itself, performs them
using tools, verifies the outcome independently, and reports back with evidence.

## Core idea: the agent loop
A custom loop (no agent frameworks) where an LLM with function calling chooses actions.

    User task
       -> Planner: writes a rough plan, revises it as it goes
       -> LOOP:
            LLM chooses next action (tool + arguments)
            Tool executor runs it
            Observation (result or error) goes back to the LLM
            Memory updated with key facts
          until the LLM says "done" or the step limit is hit
       -> Verifier: independently checks the goal was actually met
       -> Reporter: concise summary + evidence

## Tech stack
- Python 3.12, custom loop (no LangChain/LangGraph/CrewAI)
- Gemini API with function calling (key in .env)
- Playwright for the browser tool
- Flask + SQLite for the mock company app (invoice system)
- pdfplumber for reading PDF invoices
- JSON trace file per run, saved in /runs

## Tools
1. File tools: list_files, read_file (including PDF)
2. Browser tool: open_url, click, type, read_page (simplified text + list of
   clickable/input elements, not raw HTML)
3. App/API tool: direct calls to the mock company app
4. ask_user: asks the human for clarification or approval

## Mock company app
Small Flask + SQLite invoice system: login page, "Add Invoice" form (vendor, amount,
due date), invoice list page. Stable element IDs so the browser agent can target them.
Seeded with sample data. Sample invoice PDFs live in sample_data/.

## Memory
A simple state object (facts found so far, plan, actions done) included in every LLM
call, so information from step 2 is still available at step 6.

## Reliability
- Tool errors are returned to the LLM as observations, never crashes
- Retry limit per action (max 2)
- Alternative strategy when one tool fails (e.g. browser fails, try the API)
- Loop detection: same action 3 times means force a new approach or ask the user
- Global step limit and time budget

## Verification
Never trust the LLM saying "done." The verifier independently checks the result,
for example by querying the database or reloading the invoice list and comparing the
stored values with the expected values. If the check fails, the agent goes back and
fixes it.

## Human in the loop
ask_user is used when: several matches exist (ambiguity), information is missing, or an
action is risky or irreversible.

## Generalization
agent.py contains no invoice-specific logic. Task knowledge lives only in the tools and
the system prompt. The same code must handle different tasks (for example "update the
due date of invoice 102" or "list all overdue invoices into a file").

## Safety
Runs only against the local mock app, with a domain allowlist and approval required for
destructive actions.

## Build phases
1. Minimal loop with file tools, step limit, trace logging
2. Mock company app
3. Browser tool
4. Memory and planning
5. Reliability (retries, loop detection, ask_user)
6. Verifier and final report
7. README, diagram, demo video, limitations