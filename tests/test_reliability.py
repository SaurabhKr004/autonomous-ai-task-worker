import pytest
from agent.agent import ASK_USER_DECLARATION
from agent.config import LOOP_DETECTION_THRESHOLD, MAX_RETRIES_PER_ACTION
from tools.browser_tools import _is_allowed

def test_ask_user_declaration():
    assert ASK_USER_DECLARATION["name"] == "ask_user"
    assert "question" in ASK_USER_DECLARATION["parameters"]["properties"]
    assert "question" in ASK_USER_DECLARATION["parameters"]["required"]

def test_wildcard_domain_allowed():
    assert _is_allowed("https://example.com") is True
    assert _is_allowed("http://localhost:5000") is True
    assert _is_allowed("https://google.com") is True

def test_reliability_constants():
    assert LOOP_DETECTION_THRESHOLD >= 3
    assert MAX_RETRIES_PER_ACTION >= 2
