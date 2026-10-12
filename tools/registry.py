"""
registry.py — Tool registry.

Maps tool names to their Python functions and JSON schemas.
The agent loop uses this to:
  1. Tell the LLM what tools are available (the schemas).
  2. Look up and call the right function when the LLM picks a tool.

Adding a new tool is simple:
  1. Write a function in tools/
  2. Call registry.register(...) with its name, function, and schema.
"""


class ToolRegistry:
    """
    A container that holds all available tools.

    Each tool has:
      - name (str): unique identifier, e.g. "list_files"
      - func (callable): the Python function to run
      - declaration (dict): Gemini function-calling schema
    """

    def __init__(self):
        # Internal storage: name → {func, declaration}
        self._tools: dict[str, dict] = {}

    def register(self, name: str, func: callable, declaration: dict):
        """
        Register a new tool.

        Args:
            name: Tool name (must match the name in the declaration).
            func: Python function that implements the tool.
            declaration: Gemini function declaration dict with keys:
                         "name", "description", "parameters".
        """
        self._tools[name] = {
            "func": func,
            "declaration": declaration,
        }

    def get_func(self, name: str) -> callable:
        """Look up a tool's function by name. Returns None if not found."""
        tool = self._tools.get(name)
        return tool["func"] if tool else None

    def get_all_declarations(self) -> list[dict]:
        """
        Return all tool schemas as a list.
        This is what gets sent to the LLM so it knows what tools exist.
        """
        return [t["declaration"] for t in self._tools.values()]

    def list_names(self) -> list[str]:
        """Return a list of all registered tool names."""
        return list(self._tools.keys())
