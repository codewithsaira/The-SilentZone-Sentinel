"""SQLite Database layer for The SilentZone Sentinel.
Handles user authentication, password resets, and historical flood assessment report storage.
"""
import hashlib
import json
import sqlite3
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "sentinel.db"


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite database tables and seeds default user accounts."""
    with get_conn() as conn:
        cursor = conn.cursor()
        
        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT DEFAULT 'Field Coordinator',
                created_at TEXT NOT NULL
            )
        """)
        
        # 2. Search & Scan Reports Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                operator_name TEXT NOT NULL,
                area_name TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                radius_km REAL NOT NULL,
                total_villages INTEGER NOT NULL,
                total_flooded INTEGER NOT NULL,
                total_silent INTEGER NOT NULL,
                total_pop_affected INTEGER NOT NULL,
                silent_pop INTEGER NOT NULL,
                summary_json TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # Seed initial accounts if not present
        default_users = [
            ("admin", "admin@silentzonesentinel.pk", "admin123", "System Administrator", "Admin"),
            ("junaid", "junaid@silentzonesentinel.pk", "junaid123", "Malik Junaid Ahmad", "Lead Researcher & Developer"),
            ("sairakhan", "saira@silentzonesentinel.pk", "saira123", "Saira Khan", "Lead System Architect & Engineer"),
            ("saira", "saira.khan@silentzonesentinel.pk", "saira123", "Saira Khan", "Lead System Architect & Engineer"),
        ]
        
        for u, e, p, n, r in default_users:
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (u, e))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (username, email, password_hash, name, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (u.lower(), e.lower(), hash_pw(p), n, r, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()


# Initialize database on module import
init_db()


def authenticate_user(identifier: str, password: str) -> dict | None:
    """Authenticates a user via Username or Gmail/Email address."""
    id_clean = identifier.strip().lower()
    p_hash = hash_pw(password)
    
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, name, role, created_at 
            FROM users 
            WHERE (username = ? OR email = ?) AND password_hash = ?
        """, (id_clean, id_clean, p_hash))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def check_user_exists(username: str, email: str) -> tuple[bool, str]:
    """Checks if a username or email is already registered in SQLite."""
    u_clean = username.strip().lower()
    e_clean = email.strip().lower()
    
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, email FROM users WHERE username = ?", (u_clean,))
        if cursor.fetchone():
            return True, f"Username '{u_clean}' already exists. Please choose another username or log in."
            
        cursor.execute("SELECT username, email FROM users WHERE email = ?", (e_clean,))
        if cursor.fetchone():
            return True, f"Email address '{e_clean}' is already registered. Please log in or use Forgot Password."
            
    return False, ""


def register_user(username: str, email: str, password: str, name: str) -> tuple[bool, str]:
    """Directly registers a new user in SQLite after validation."""
    u_clean = username.strip().lower()
    e_clean = email.strip().lower()
    
    if not u_clean or len(u_clean) < 3:
        return False, "Username must be at least 3 characters long."
    if not e_clean or "@" not in e_clean:
        return False, "Please provide a valid Gmail/Email address."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."
        
    exists, msg = check_user_exists(u_clean, e_clean)
    if exists:
        return False, msg
        
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, name, role, created_at)
                VALUES (?, ?, ?, ?, 'Field Coordinator', ?)
            """, (u_clean, e_clean, hash_pw(password), name.strip() or u_clean, time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        return True, "Account registered successfully in database! You can now log in."
    except Exception as e:
        return False, f"Database registration error: {str(e)}"


def reset_user_password(identifier_or_email: str, new_password: str) -> tuple[bool, str]:
    """Resets user password in SQLite database via registered email or username."""
    id_clean = identifier_or_email.strip().lower()
    if len(new_password) < 4:
        return False, "New password must be at least 4 characters long."
        
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users WHERE username = ? OR email = ?", (id_clean, id_clean))
        row = cursor.fetchone()
        if not row:
            return False, f"No account found matching '{id_clean}'. Please verify your Gmail or username."
            
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_pw(new_password), row["id"]))
        conn.commit()
        return True, f"Password for account '{row['username']}' has been updated successfully! You can now log in."


def save_scan_report(username: str, operator_name: str, area_name: str, lat: float, lon: float, radius_km: float, summary: dict, details: dict) -> int:
    """Saves a completed area flood scan to the database history."""
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scan_reports (
                    username, operator_name, area_name, lat, lon, radius_km,
                    total_villages, total_flooded, total_silent, total_pop_affected, silent_pop,
                    summary_json, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username,
                operator_name,
                area_name,
                float(lat),
                float(lon),
                float(radius_km),
                int(summary.get("total_villages", 0)),
                int(summary.get("total_flooded", 0)),
                int(summary.get("total_silent", 0)),
                int(summary.get("total_pop_affected", 0)),
                int(summary.get("silent_pop", 0)),
                json.dumps(summary, ensure_ascii=False),
                json.dumps(details, ensure_ascii=False),
                time.strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            return cursor.lastrowid
    except Exception:
        return -1


def get_all_reports(limit: int = 50) -> list[dict]:
    """Retrieves all past scan reports from SQLite."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, operator_name, area_name, lat, lon, radius_km,
                   total_villages, total_flooded, total_silent, total_pop_affected, silent_pop,
                   summary_json, details_json, created_at
            FROM scan_reports
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
