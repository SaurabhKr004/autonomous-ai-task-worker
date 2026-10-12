"""
streamlit_app.py — Interactive Web Dashboard for Autonomous AI Task Worker.

Allows users to:
1. Launch autonomous tasks in plain English.
2. View real-time planner steps, tools invoked, and working memory.
3. Inspect saved execution traces from /runs.
"""

import os
import json
import glob
import streamlit as st
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

from agent.agent import run_agent
from agent.config import MODEL_NAME, MAX_STEPS, TIME_BUDGET_SECONDS, RUNS_DIR
from main import build_registry


st.set_page_config(
    page_title="AI Task Worker Dashboard",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Autonomous AI Task Worker")
st.caption("Custom agent loop with Gemini function-calling, browser control & working memory.")

# ---- Sidebar ----
with st.sidebar:
    st.header("⚙️ Configuration")
    st.write(f"**Model:** `{MODEL_NAME}`")
    st.write(f"**Max Steps:** `{MAX_STEPS}`")
    st.write(f"**Time Budget:** `{TIME_BUDGET_SECONDS}s`")
    
    st.markdown("---")
    st.header("📜 Execution Traces")
    os.makedirs(RUNS_DIR, exist_ok=True)
    trace_files = sorted(glob.glob(os.path.join(RUNS_DIR, "run_*.json")), reverse=True)
    
    if trace_files:
        selected_file = st.selectbox(
            "Select past run trace:",
            trace_files,
            format_func=lambda f: os.path.basename(f)
        )
        if selected_file:
            with open(selected_file, "r", encoding="utf-8") as f:
                trace_data = json.load(f)
            st.metric("Status", trace_data.get("status", "unknown").upper())
            st.metric("Steps Taken", trace_data.get("steps_taken", 0))
            with st.expander("View Full Trace JSON"):
                st.json(trace_data)
    else:
        st.info("No runs recorded yet in `/runs`.")

# ---- Main Area ----
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎯 Assign a Task")
    
    sample_tasks = [
        "List all files in sample_data/ and tell me what is in them.",
        "Open http://127.0.0.1:5000/login, log in with username 'admin' and password 'secret', and read the invoices page.",
        "Navigate to https://example.com, read the page, and summarize what you find.",
    ]
    
    selected_sample = st.selectbox("Choose a sample task preset (optional):", ["-- Select a preset or type below --"] + sample_tasks)
    
    initial_text = ""
    if selected_sample != "-- Select a preset or type below --":
        initial_text = selected_sample

    task_input = st.text_area("Task description in plain English:", value=initial_text, height=100)
    run_button = st.button("🚀 Start Agent Worker", type="primary", use_container_width=True)

with col2:
    st.subheader("💡 Capabilities")
    st.markdown("""
    - **Planner**: Outlines an actionable plan before acting.
    - **Working Memory**: Injects discovered facts & past actions into each turn.
    - **Browser Automation**: Navigates websites, clicks, types, and reads pages.
    - **Reliability Guards**: Auto loop detection & retry limit prevention.
    - **Human-in-the-Loop**: Supports `ask_user` questions.
    """)

# ---- Agent Execution ----
if run_button:
    if not task_input.strip():
        st.warning("Please provide a task description first.")
    else:
        st.markdown("---")
        st.subheader("⚡ Live Execution")
        
        status_box = st.status("Agent worker is starting up...", expanded=True)
        
        step_feed = []
        
        def handle_step(step_info):
            step_feed.append(step_info)
            s_type = step_info.get("type")
            if s_type == "function_call":
                status_box.write(f"🔧 **Step {step_info.get('step')}:** `{step_info.get('tool')}`")
            elif s_type == "done":
                status_box.write(f"✅ **Done:** {step_info.get('summary')}")
            elif s_type == "text":
                status_box.write(f"💭 {step_info.get('content')[:120]}...")

        registry = build_registry()
        
        try:
            result = run_agent(
                task=task_input,
                registry=registry,
                step_callback=handle_step,
            )
            
            status_box.update(
                label=f"Execution Finished: {result['status'].upper()} in {result['elapsed_seconds']}s",
                state="complete" if result['status'] == "done" else "error"
            )
            
            st.success(f"**Final Summary:** {result['summary']}")
            
            # Display memory and results
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Final Report & Verification", "Steps Detail", "Working Memory", "Raw Output"])
            
            with tab1:
                st.subheader(f"Verdict: {result.get('verification', {}).get('verdict', 'N/A')}")
                st.markdown(result.get("report_text", "No report generated."))

            with tab2:
                for step in result.get("steps", []):
                    st.write(step)
            
            with tab3:
                mem = result.get("memory", {})
                st.write("**Plan:**", mem.get("plan", "No plan"))
                st.write("**Facts:**", mem.get("facts", []))
                
            with tab4:
                st.json(result)
                
        except Exception as e:
            status_box.update(label="Execution Failed with Error", state="error")
            st.error(f"Error executing agent: {e}")
