import pytest
from agent.memory import Memory
from agent.agent import UPDATE_PLAN_DECLARATION

def test_memory_facts_and_plan():
    mem = Memory("Test task")
    assert mem.task == "Test task"
    
    mem.set_plan("1. Step one\n2. Step two")
    assert "Step one" in mem.plan
    
    mem.add_fact("Found invoice 101")
    mem.add_fact("Found invoice 101")  # Deduplication test
    assert len(mem.facts) == 1
    assert mem.facts[0] == "Found invoice 101"

def test_memory_prompt_formatting():
    mem = Memory("Process invoice")
    mem.set_plan("1. Find invoice\n2. Add to app")
    mem.add_fact("Vendor is Acme")
    mem.record_action("read_file", {"path": "invoice.txt"}, "Total: $500")
    
    prompt_str = mem.to_prompt_string()
    
    assert "## Current Task\nProcess invoice" in prompt_str
    assert "## Current Plan\n1. Find invoice\n2. Add to app" in prompt_str
    assert "## Facts Discovered\n- Vendor is Acme" in prompt_str
    assert "## Recent Actions" in prompt_str
    assert "read_file" in prompt_str
    assert "Total: $500" in prompt_str

def test_update_plan_declaration():
    assert UPDATE_PLAN_DECLARATION["name"] == "update_plan"
    assert "plan" in UPDATE_PLAN_DECLARATION["parameters"]["properties"]
    assert "plan" in UPDATE_PLAN_DECLARATION["parameters"]["required"]
