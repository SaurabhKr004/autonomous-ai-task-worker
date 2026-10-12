import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'invoices.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS invoices')
    c.execute('''
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL
        )
    ''')
    
    # insert sample data
    c.execute("INSERT INTO invoices (vendor, amount, due_date) VALUES ('Acme Corp', 1500.00, '2026-11-01')")
    c.execute("INSERT INTO invoices (vendor, amount, due_date) VALUES ('Globex Inc', 450.50, '2026-10-15')")
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH} with sample data.")

if __name__ == '__main__':
    init_db()
