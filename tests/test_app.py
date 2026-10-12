import os
import pytest
from app.app import app
from app.init_db import init_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # Re-initialize DB using the helper script to ensure clean state
    init_db()
    with app.test_client() as client:
        yield client

def test_login_page_loads(client):
    rv = client.get('/login')
    assert rv.status_code == 200
    assert b'id="login-btn"' in rv.data

def test_invoice_list_loads(client):
    rv = client.get('/invoices')
    assert rv.status_code == 200
    assert b'id="invoice-list"' in rv.data
    assert b'Acme Corp' in rv.data  # Ensure seed data is rendered

def test_add_invoice_page(client):
    rv = client.get('/add_invoice')
    assert rv.status_code == 200
    assert b'id="vendor-input"' in rv.data

def test_add_invoice_post(client):
    rv = client.post('/add_invoice', data=dict(
        vendor="Test Vendor",
        amount="99.99",
        due_date="2026-12-31"
    ), follow_redirects=True)
    
    assert rv.status_code == 200
    assert b'Test Vendor' in rv.data
    assert b'99.99' in rv.data
