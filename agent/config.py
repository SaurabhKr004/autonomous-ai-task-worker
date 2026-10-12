"""
config.py — Central configuration for the agent.

All tuneable knobs live here so they're easy to find and change.
"""

# ---------- LLM settings ----------
# Which Gemini model to use for the agent's "brain"
MODEL_NAME = "gemini-3.8-flash"

# ---------- Loop limits ----------
# Maximum number of tool-call steps before the agent is forced to stop.
# Prevents runaway loops that burn API credits.
MAX_STEPS = 15

# Maximum wall-clock time (seconds) for the entire run.
TIME_BUDGET_SECONDS = 300  # 5 minutes

# ---------- Retry settings ----------
# How many times a single action can be retried before giving up.
MAX_RETRIES_PER_ACTION = 2

# If the agent repeats the exact same action this many times, force a
# new approach or ask the user for help.
LOOP_DETECTION_THRESHOLD = 3

# ---------- Paths ----------
# Directory where JSON traces are saved (one file per run).
RUNS_DIR = "runs"

# ---------- Safety ----------
# Browser is allowed to visit URLs on these domains (use "*" to allow all domains).
ALLOWED_DOMAINS = ["*"]
