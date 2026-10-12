from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_mock_key'

DB_PATH = os.path.join(os.path.dirname(__file__), 'invoices.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Dummy authentication, any credentials work
        return redirect(url_for('list_invoices'))
    return render_template('login.html')

@app.route('/invoices')
def list_invoices():
    db = get_db()
    cur = db.execute('SELECT * FROM invoices ORDER BY id DESC')
    invoices = cur.fetchall()
    return render_template('list.html', invoices=invoices)

@app.route('/add_invoice', methods=['GET', 'POST'])
def add_invoice():
    if request.method == 'POST':
        vendor = request.form.get('vendor')
        amount = request.form.get('amount')
        due_date = request.form.get('due_date')
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0.0

        db = get_db()
        db.execute('INSERT INTO invoices (vendor, amount, due_date) VALUES (?, ?, ?)', (vendor, amount, due_date))
        db.commit()
        return redirect(url_for('list_invoices'))
    
    return render_template('add_invoice.html')

if __name__ == '__main__':
   app.run(debug=False, use_reloader=False, port=5000)
