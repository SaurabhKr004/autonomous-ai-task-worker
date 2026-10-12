"""
browser_tools.py — Playwright-based browser tools.

This module provides tools for the agent to interact with web pages.
Allows navigating to allowed domains, clicking, typing, and reading the page.
"""

from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
from agent.config import ALLOWED_DOMAINS

# Global state for the browser so we don't restart it on every action.
_playwright = None
_browser = None
_page = None

def _get_page():
    """Ensure the browser is running and return the active page."""
    global _playwright, _browser, _page
    if _page is None:
        _playwright = sync_playwright().start()
        # Using headless=True for automated agent.
        _browser = _playwright.chromium.launch(headless=True)
        context = _browser.new_context()
        _page = context.new_page()
    return _page

def _is_allowed(url: str) -> bool:
    """Check if the URL domain is in the allowed list."""
    if "*" in ALLOWED_DOMAINS or not ALLOWED_DOMAINS:
        return True
    domain = urlparse(url).hostname
    if not domain:
        return False
    return domain in ALLOWED_DOMAINS

def open_url(args: dict) -> str:
    """Navigate to a URL."""
    url = args.get("url", "")
    if not _is_allowed(url):
        return f"Error: Domain not allowed. Allowed domains are: {ALLOWED_DOMAINS}"
    
    page = _get_page()
    try:
        page.goto(url)
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception as e:
        return f"Error opening URL: {str(e)}"
    return f"Successfully opened {url}."

def click(args: dict) -> str:
    """Click an element by CSS selector."""
    selector = args.get("selector", "")
    page = _get_page()
    try:
        page.locator(selector).click(timeout=3000)
        page.wait_for_load_state("networkidle", timeout=3000)
    except Exception as e:
        return f"Error clicking '{selector}': {str(e)}"
    return f"Successfully clicked {selector}."

def type_text(args: dict) -> str:
    """Type text into an input field."""
    selector = args.get("selector", "")
    text = args.get("text", "")
    page = _get_page()
    try:
        page.locator(selector).fill(text, timeout=3000)
    except Exception as e:
        return f"Error typing into '{selector}': {str(e)}"
    return f"Successfully typed text into {selector}."

def read_page(args: dict) -> str:
    """Read the page text and extract interactive elements."""
    page = _get_page()
    try:
        text_content = page.evaluate('document.body.innerText')
        
        elements_info = page.evaluate('''() => {
            const elements = Array.from(document.querySelectorAll('button, input, a'));
            return elements.map(el => {
                let id = el.id ? `#${el.id}` : '';
                let type = el.tagName.toLowerCase();
                if (type === 'input') {
                   type = `${el.type} input`;
                }
                let text = el.innerText || el.value || el.placeholder || el.name || '';
                return `${type}${id} - "${text.trim()}"`;
            });
        }''')
        
        interactive_str = "\n".join(elements_info)
        
        result = (
            "--- PAGE TEXT ---\n"
            f"{text_content[:2000]}\n\n"
            "--- INTERACTIVE ELEMENTS ---\n"
            f"{interactive_str}"
        )
        return result
    except Exception as e:
        return f"Error reading page: {str(e)}"

# Declarations for Gemini
OPEN_URL_DECLARATION = {
    "name": "open_url",
    "description": "Open a webpage in the browser. You must specify the full URL including scheme.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The full URL to open (e.g. http://127.0.0.1:5000/)"}
        },
        "required": ["url"]
    }
}

CLICK_DECLARATION = {
    "name": "click",
    "description": "Click an element on the current page using a CSS selector.",
    "parameters": {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of the element to click (e.g. #login-btn)"}
        },
        "required": ["selector"]
    }
}

TYPE_TEXT_DECLARATION = {
    "name": "type_text",
    "description": "Type text into an input field on the current page.",
    "parameters": {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of the input field (e.g. #username-input)"},
            "text": {"type": "string", "description": "The text to type"}
        },
        "required": ["selector", "text"]
    }
}

READ_PAGE_DECLARATION = {
    "name": "read_page",
    "description": "Read the text content of the page and list interactive elements (buttons, inputs, links).",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
