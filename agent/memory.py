"""
memory.py — The agent's working memory.

This is a simple state object that gets passed into every LLM call
so the model can remember what it has learned, what it has done,
and what it plans to do next.

Think of it as the agent's "scratchpad" that persists across steps.
"""


class Memory:
    """Holds everything the agent needs to remember between steps."""

    def __init__(self, task: str):
        # The original task the user asked for (never changes).
        self.task: str = task

        # Key facts the agent has discovered (e.g. "vendor is Acme Corp").
        # Each fact is a short string.
        self.facts: list[str] = []

        # The agent's current plan — a plain-text description of
        # the remaining steps it intends to take.
        self.plan: str = ""

        # Log of every action the agent has taken and its result.
        # Each entry is a dict: {"tool": ..., "args": ..., "result": ...}
        self.actions: list[dict] = []

    # ---- Helper methods ----

    def add_fact(self, fact: str):
        """Save a new fact the agent discovered."""
        if fact and fact not in self.facts:
            self.facts.append(fact)

    def set_plan(self, plan: str):
        """Replace the current plan with an updated one."""
        self.plan = plan

    def record_action(self, tool_name: str, args: dict, result: str):
        """Log one action that was executed."""
        self.actions.append({
            "tool": tool_name,
            "args": args,
            "result": result,
        })

    def to_dict(self) -> dict:
        """Convert to a plain dict (for JSON trace logging)."""
        return {
            "task": self.task,
            "facts": self.facts,
            "plan": self.plan,
            "actions": self.actions,
        }

    def to_prompt_string(self) -> str:
        """
        Format memory as a readable string to include in the LLM prompt.
        This is how the model "sees" everything it knows so far.
        """
        parts = [f"## Current Task\n{self.task}"]

        if self.plan:
            parts.append(f"## Current Plan\n{self.plan}")

        if self.facts:
            facts_str = "\n".join(f"- {f}" for f in self.facts)
            parts.append(f"## Facts Discovered\n{facts_str}")

        if self.actions:
            # Show only the last 5 actions to save context window space.
            recent = self.actions[-5:]
            actions_str = ""
            for i, act in enumerate(recent):
                # Truncate very long results to avoid blowing up the prompt.
                result_preview = str(act["result"])[:500]
                actions_str += (
                    f"\n### Step {len(self.actions) - len(recent) + i + 1}\n"
                    f"Tool: {act['tool']}\n"
                    f"Args: {act['args']}\n"
                    f"Result: {result_preview}\n"
                )
            parts.append(f"## Recent Actions{actions_str}")

        return "\n\n".join(parts)
