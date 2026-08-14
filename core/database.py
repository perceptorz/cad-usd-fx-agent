"""
Database module for LooniePulse FX.
Handles SQLite storage for rate snapshots, alert rules, and notification logs.
"""

import os
import sqlite3
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rates.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Rate snapshots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rate_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        spot_rate REAL NOT NULL,
        td_retail_rate REAL NOT NULL,
        td_spread_pct REAL NOT NULL,
        norbert_rate REAL NOT NULL,
        source TEXT DEFAULT 'live'
    )
    """)
    
    # Alert rules
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alert_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_rate REAL NOT NULL,
        comparison TEXT DEFAULT '>=',
        target_type TEXT DEFAULT 'spot', -- 'spot' or 'td_retail'
        channel TEXT DEFAULT 'all',      -- 'system', 'webhook', 'all'
        webhook_url TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        triggered_at TEXT,
        trigger_count INTEGER DEFAULT 0
    )
    """)
    
    # Notification logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        channel TEXT NOT NULL,
        rate_at_trigger REAL NOT NULL
    )
    """)
    
    # Seed default alerts if table empty
    cursor.execute("SELECT COUNT(*) FROM alert_rules")
    if cursor.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        cursor.execute("""
        INSERT INTO alert_rules (target_rate, comparison, target_type, channel, is_active, created_at)
        VALUES (0.7300, '>=', 'spot', 'all', 1, ?),
               (0.7400, '>=', 'spot', 'all', 1, ?),
               (0.7200, '>=', 'td_retail', 'all', 1, ?)
        """, (now, now, now))
        
    conn.commit()
    conn.close()

def log_rate(spot_rate, td_retail_rate, td_spread_pct, norbert_rate, source="live"):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO rate_history (timestamp, spot_rate, td_retail_rate, td_spread_pct, norbert_rate, source)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (now, spot_rate, td_retail_rate, td_spread_pct, norbert_rate, source))
    conn.commit()
    conn.close()

def get_recent_history(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT timestamp, spot_rate, td_retail_rate, td_spread_pct, norbert_rate
    FROM rate_history
    ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows][::-1]

def get_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alert_rules ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_alert(target_rate, comparison=">=", target_type="spot", channel="all", webhook_url=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO alert_rules (target_rate, comparison, target_type, channel, webhook_url, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (target_rate, comparison, target_type, channel, webhook_url, now))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def delete_alert(alert_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alert_rules WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

def toggle_alert(alert_id, is_active):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alert_rules SET is_active = ? WHERE id = ?", (1 if is_active else 0, alert_id))
    conn.commit()
    conn.close()

def log_notification(title, message, channel, rate_at_trigger):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO notification_logs (timestamp, title, message, channel, rate_at_trigger)
    VALUES (?, ?, ?, ?, ?)
    """, (now, title, message, channel, rate_at_trigger))
    conn.commit()
    conn.close()

def get_notification_logs(limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notification_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
