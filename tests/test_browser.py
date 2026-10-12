import time
import threading
from tools.browser_tools import open_url, click, type_text, read_page
from app.init_db import init_db
from app.app import app

def start_server():
    app.run(port=5000, use_reloader=False)

if __name__ == '__main__':
    print("Initializing DB...")
    init_db()

    print("Starting server background thread...")
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for the server to spin up
    time.sleep(2)

    print("\n--- Testing Browser Tools ---")
    print("1. Opening login page...")
    print(open_url({"url": "http://127.0.0.1:5000/login"}))
    
    print("2. Typing credentials...")
    print(type_text({"selector": "#username-input", "text": "agent"}))
    print(type_text({"selector": "#password-input", "text": "secret"}))
    
    print("3. Clicking login...")
    print(click({"selector": "#login-btn"}))
    
    time.sleep(1) # wait for redirect

    print("4. Reading page...")
    result = read_page({})
    print(result)

    assert "--- PAGE TEXT ---" in result
    assert "Acme Corp" in result or "Invoice" in result
    print("\nSUCCESS! Browser automation interacts with the Flask app.")
