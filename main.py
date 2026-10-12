"""
main.py — Entry point for the Autonomous AI Task Worker.

Usage:
    python main.py "Your task in plain English"

Example:
    python main.py "List all files in sample_data/ and tell me what's in them"

This file:
  1. Loads environment variables (.env).
  2. Registers all available tools.
  3. Hands the task to the agent loop.
  4. Prints the final result.
"""

import sys
from dotenv import load_dotenv

from agent.agent import (
    run_agent, DONE_DECLARATION, SAVE_FACT_DECLARATION,
    UPDATE_PLAN_DECLARATION, ASK_USER_DECLARATION
)
from tools.registry import ToolRegistry
from tools.file_tools import (
    list_files, LIST_FILES_DECLARATION,
    read_file, READ_FILE_DECLARATION,
)
from tools.browser_tools import (
    open_url, OPEN_URL_DECLARATION,
    click, CLICK_DECLARATION,
    type_text, TYPE_TEXT_DECLARATION,
    read_page, READ_PAGE_DECLARATION,
)


def build_registry() -> ToolRegistry:
    """
    Create a ToolRegistry and register all available tools.

    This is the ONLY place where tools are wired up.
    To add a new tool, import it and register it here.
    """
    registry = ToolRegistry()

    # -- File tools --
    registry.register("list_files", list_files, LIST_FILES_DECLARATION)
    registry.register("read_file", read_file, READ_FILE_DECLARATION)

    # -- Browser tools --
    registry.register("open_url", open_url, OPEN_URL_DECLARATION)
    registry.register("click", click, CLICK_DECLARATION)
    registry.register("type_text", type_text, TYPE_TEXT_DECLARATION)
    registry.register("read_page", read_page, READ_PAGE_DECLARATION)

    # -- Built-in agent tools (handled by the loop, not external functions) --
    # We still register their declarations so the LLM knows they exist.
    # The agent loop intercepts these by name before looking them up.
    registry.register("done", None, DONE_DECLARATION)
    registry.register("save_fact", None, SAVE_FACT_DECLARATION)
    registry.register("update_plan", None, UPDATE_PLAN_DECLARATION)
    registry.register("ask_user", None, ASK_USER_DECLARATION)

    return registry


def main():
    """Parse CLI args, build tools, run the agent."""
    # Load API key from .env
    load_dotenv()

    # Get the task from command-line arguments.
    if len(sys.argv) < 2:
        print("Usage: python main.py \"Your task here\"")
        print("Example: python main.py \"List all files in sample_data/\"")
        sys.exit(1)

    task = " ".join(sys.argv[1:])

    # Build the tool registry.
    registry = build_registry()

    # Run the agent loop.
    result = run_agent(task, registry)

    # Print a clean final summary.
    print(f"\n{'-'*40}")
    print(f"Status:  {result['status']}")
    print(f"Summary: {result['summary']}")
    print(f"Steps:   {result['steps_taken']}")
    print(f"Time:    {result['elapsed_seconds']}s")
    print(f"{'─'*40}")


if __name__ == "__main__":
    main()
