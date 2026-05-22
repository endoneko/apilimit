import sqlite3
import json
import os
import time
from threading import local

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'aipg.db')

_local_data = local()

def get_db():
    if not hasattr(_local_data, 'conn'):
        _local_data.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local_data.conn.row_factory = sqlite3.Row
    return _local_data.conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, username TEXT, role TEXT, status TEXT,
        quota_total INTEGER, quota_used INTEGER, rpm INTEGER, tpm INTEGER,
        ip_whitelist TEXT, expires_at TEXT
    )''')
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN password TEXT")
    except sqlite3.OperationalError:
        pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        key TEXT PRIMARY KEY, user_id TEXT, is_active INTEGER
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, timestamp REAL, provider TEXT, target_url TEXT,
        status_code INTEGER, tokens_estimated INTEGER
    )''')
    
    conn.commit()

    # Load static json to db (Initialization Sync)
    users_file = os.path.join(CONFIG_DIR, 'users.json')
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for u in data.get('users', []):
                whitelist_str = ",".join(u.get('ip_whitelist', []))
                c.execute("INSERT OR REPLACE INTO users (id, username, password, role, status, quota_total, quota_used, rpm, tpm, ip_whitelist, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (u['id'], u['username'], u.get('password', ''), u['role'], u['status'], u['quota']['total'], u.get('quota', {}).get('used', 0), u['rate_limits']['rpm'], u['rate_limits']['tpm'], whitelist_str, u.get('expires_at')))
                
                # Mock a ready-to-use API Key format for demonstration 
                dummy_key = f"aip_{u['username']}_key"
                c.execute("INSERT OR REPLACE INTO api_keys (key, user_id, is_active) VALUES (?, ?, 1)", (dummy_key, u['id']))
    conn.commit()

def check_api_key(api_key):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT u.* FROM users u JOIN api_keys k ON u.id = k.user_id WHERE k.key = ? AND k.is_active = 1", (api_key,))
    return c.fetchone()

def deduct_quota(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET quota_used = quota_used + ? WHERE id = ?", (amount, user_id))
    conn.commit()

def log_request(user_id, provider, url, status, tokens):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, timestamp, provider, target_url, status_code, tokens_estimated) VALUES (?, ?, ?, ?, ?, ?)", 
             (user_id, time.time(), provider, url, status, tokens))
    conn.commit()

def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT count(*) as total_reqs, sum(tokens_estimated) as total_tokens FROM logs")
    res = c.fetchone()
    return {"total_requests": res['total_reqs'], "total_tokens": res['total_tokens'] if res['total_tokens'] else 0}

def get_recent_logs(limit=50):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    return [dict(row) for row in c.fetchall()]

def get_users():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, username, role, status, quota_total, quota_used, rpm, tpm FROM users")
    return [dict(row) for row in c.fetchall()]

def get_user_by_username(username):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    return dict(row) if row else None

def get_user_api_keys(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT key, is_active FROM api_keys WHERE user_id = ?", (user_id,))
    return [dict(row) for row in c.fetchall()]

def get_user_logs(user_id, limit=20):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
    return [dict(row) for row in c.fetchall()]
def update_user_limits(user_id, quota_total, rpm, tpm, status):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET quota_total = ?, rpm = ?, tpm = ?, status = ? WHERE id = ?", (quota_total, rpm, tpm, status, user_id))
    conn.commit()

def generate_api_key(user_id, username):
    import uuid
    conn = get_db()
    c = conn.cursor()
    new_key = f"aip_{username}_{uuid.uuid4().hex[:8]}"
    c.execute("INSERT INTO api_keys (key, user_id, is_active) VALUES (?, ?, 1)", (new_key, user_id))
    conn.commit()
    return new_key

def create_user(username, password, role='user'):
    import uuid
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    if c.fetchone():
        return False # Username already exists
    
    new_id = f"user_{uuid.uuid4().hex[:8]}"
    # 默认赠送额度：10万Token，限速60RPM，50000TPM
    quota_total = 100000
    rpm = 60
    tpm = 50000
    c.execute("INSERT INTO users (id, username, password, role, status, quota_total, quota_used, rpm, tpm, ip_whitelist, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, username, password, role, 'active', quota_total, 0, rpm, tpm, '', None))
    conn.commit()
    return True
