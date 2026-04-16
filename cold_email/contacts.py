"""
Contact Manager - Manage contacts and track email status.
"""
import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path(__file__).parent / "contacts.db"


def init_db():
    """Initialize the contacts database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            company TEXT,
            domain TEXT,
            role TEXT,
            status TEXT DEFAULT 'pending',
            email_confidence REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            subject TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_id TEXT,
            status TEXT DEFAULT 'sent',
            FOREIGN KEY (contact_id) REFERENCES contacts(id)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)
    """)
    
    conn.commit()
    conn.close()


def import_contacts_from_csv(csv_path: str) -> dict:
    """
    Import contacts from a CSV file.
    
    Expected CSV columns: name, company, domain (optional), role (optional)
    
    Returns:
        dict with 'imported', 'skipped', 'errors'
    """
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    imported = 0
    skipped = 0
    errors = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    name = row.get('name', '').strip()
                    company = row.get('company', '').strip()
                    domain = row.get('domain', '').strip()
                    role = row.get('role', '').strip()
                    email = row.get('email', '').strip()
                    
                    if not name:
                        skipped += 1
                        continue
                    
                    # If no domain, try to extract from company name
                    if not domain and company:
                        domain = company.lower().replace(' ', '') + '.com'
                    
                    # Check for duplicate
                    cursor.execute(
                        "SELECT id FROM contacts WHERE name = ? AND company = ?",
                        (name, company)
                    )
                    if cursor.fetchone():
                        skipped += 1
                        continue
                    
                    cursor.execute("""
                        INSERT INTO contacts (name, email, company, domain, role)
                        VALUES (?, ?, ?, ?, ?)
                    """, (name, email, company, domain, role))
                    
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"Row error: {e}")
                    continue
        
        conn.commit()
        
    except Exception as e:
        errors.append(f"File error: {e}")
    finally:
        conn.close()
    
    return {'imported': imported, 'skipped': skipped, 'errors': errors}


def get_pending_contacts(limit: int = 10) -> list[dict]:
    """Get contacts that haven't been emailed yet."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM contacts 
        WHERE status = 'pending' AND email IS NOT NULL AND email != ''
        ORDER BY created_at
        LIMIT ?
    """, (limit,))
    
    contacts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return contacts


def get_contacts_needing_email(limit: int = 10) -> list[dict]:
    """Get contacts that need email discovery."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM contacts 
        WHERE (email IS NULL OR email = '') AND domain IS NOT NULL
        ORDER BY created_at
        LIMIT ?
    """, (limit,))
    
    contacts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return contacts


def update_contact_email(contact_id: int, email: str, confidence: float = 0.7):
    """Update a contact's email address."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE contacts 
        SET email = ?, email_confidence = ?, updated_at = ?
        WHERE id = ?
    """, (email, confidence, datetime.now(), contact_id))
    
    conn.commit()
    conn.close()


def mark_contact_sent(contact_id: int, subject: str, message_id: str = None):
    """Mark a contact as emailed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update status
    cursor.execute("""
        UPDATE contacts 
        SET status = 'sent', updated_at = ?
        WHERE id = ?
    """, (datetime.now(), contact_id))
    
    # Record the email
    cursor.execute("""
        INSERT INTO sent_emails (contact_id, subject, message_id)
        VALUES (?, ?, ?)
    """, (contact_id, subject, message_id))
    
    conn.commit()
    conn.close()


def mark_contact_error(contact_id: int, error: str):
    """Mark a contact with an error."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE contacts 
        SET status = 'error', notes = ?, updated_at = ?
        WHERE id = ?
    """, (error, datetime.now(), contact_id))
    
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """Get email campaign statistics."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM contacts")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contacts WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contacts WHERE status = 'sent'")
    sent = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contacts WHERE status = 'error'")
    errors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM contacts WHERE email IS NULL OR email = ''")
    no_email = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sent_emails WHERE DATE(sent_at) = DATE('now')")
    sent_today = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'pending': pending,
        'sent': sent,
        'errors': errors,
        'no_email': no_email,
        'sent_today': sent_today
    }


def list_contacts(status: str = None, limit: int = 20) -> list[dict]:
    """List contacts with optional status filter."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if status:
        cursor.execute("""
            SELECT * FROM contacts 
            WHERE status = ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (status, limit))
    else:
        cursor.execute("""
            SELECT * FROM contacts 
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
    
    contacts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return contacts


def add_contact(name: str, company: str, domain: str = None, role: str = None, email: str = None) -> int:
    """Add a single contact."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if not domain and company:
        domain = company.lower().replace(' ', '') + '.com'
    
    cursor.execute("""
        INSERT INTO contacts (name, email, company, domain, role)
        VALUES (?, ?, ?, ?, ?)
    """, (name, email, company, domain, role))
    
    contact_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return contact_id


# Test
if __name__ == "__main__":
    init_db()
    print("Database initialized!")
    
    stats = get_stats()
    print(f"\nStats: {stats}")
