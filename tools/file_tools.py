"""
file_tools.py — File-system tools for the agent.

These let the agent explore directories and read text files.
PDF support will be added in Phase 3.

Each tool function follows the same pattern:
  - Accepts a dict of arguments (from the LLM).
  - Returns a string result (which becomes the LLM's "observation").
  - NEVER raises exceptions — errors are returned as strings.
"""

import os


# ---- Tool implementations ----

def list_files(args: dict) -> str:
    """
    List all files and folders in a directory.

    Args (from LLM):
        directory (str): Path to the directory to list.

    Returns:
        A string listing each item, one per line, with [DIR] or [FILE] prefix.
    """
    directory = args.get("directory", ".")

    # Safety: don't let the agent escape the project folder.
    try:
        entries = os.listdir(directory)
    except FileNotFoundError:
        return f"Error: Directory not found: {directory}"
    except PermissionError:
        return f"Error: Permission denied: {directory}"

    if not entries:
        return f"Directory '{directory}' is empty."

    lines = []
    for entry in sorted(entries):
        full_path = os.path.join(directory, entry)
        if os.path.isdir(full_path):
            lines.append(f"[DIR]  {entry}")
        else:
            # Show file size for context.
            size = os.path.getsize(full_path)
            lines.append(f"[FILE] {entry} ({size} bytes)")

    return "\n".join(lines)


def read_file(args: dict) -> str:
    """
    Read the contents of a text file.

    Args (from LLM):
        path (str): Path to the file to read.

    Returns:
        The file contents as a string, or an error message.
    """
    path = args.get("path", "")

    if not path:
        return "Error: No file path provided."

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except UnicodeDecodeError:
        return f"Error: Cannot read '{path}' as text (it may be a binary file)."

    # Truncate very long files so we don't blow up the context window.
    max_chars = 10_000
    if len(content) > max_chars:
        content = content[:max_chars] + f"\n\n... [truncated, {len(content)} chars total]"

    return content


# ---- Gemini function-calling schemas ----
# These tell the LLM what arguments each tool expects.

LIST_FILES_DECLARATION = {
    "name": "list_files",
    "description": (
        "List all files and directories inside the given directory. "
        "Use this to explore what files are available."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Path to the directory to list. Defaults to current directory.",
            },
        },
        "required": ["directory"],
    },
}

READ_FILE_DECLARATION = {
    "name": "read_file",
    "description": (
        "Read and return the full text contents of a file. "
        "Use this to examine file contents. Currently supports text files only."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read.",
            },
        },
        "required": ["path"],
    },
}
