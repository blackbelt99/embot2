# ╔══════════════════════════════════════════════════════════════╗
# ║         Empire Bot — Persistent Database (SQLite)    ║
# ║  Har server ka data alag — restart-proof — public bot ready ║
# ╚══════════════════════════════════════════════════════════════╝

import sqlite3
import json
import os
from datetime import datetime, timezone

# Load .env from the same directory as db.py so DB_PATH is always set correctly
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except Exception:
    pass

# DB_PATH: use env var if set, otherwise next to db.py file
# Set DB_PATH in .env to ensure bot + dashboard use same file
_DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "empire.db")
DB_PATH = os.environ.get("DB_PATH", _DEFAULT_DB)

def get_conn():
    # Read DB_PATH fresh each call so .env loaded after import still works
    path = os.environ.get("DB_PATH", _DEFAULT_DB)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_conn()
    c = conn.cursor()

    # ── Guild Settings ──────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id    INTEGER PRIMARY KEY,
            prefix      TEXT    DEFAULT '$',
            bot_log     INTEGER DEFAULT 0,
            mod_log     INTEGER DEFAULT 0,
            invite_log  INTEGER DEFAULT 0,
            ticket_log  INTEGER DEFAULT 0
        )
    """)

    # ── Anti-Nuke ───────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS antinuke (
            guild_id    INTEGER PRIMARY KEY,
            enabled     INTEGER DEFAULT 0,
            punishment  TEXT    DEFAULT 'ban',
            log_channel INTEGER DEFAULT 0,
            raid_shield INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS antinuke_whitelist (
            guild_id    INTEGER,
            user_id     INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS antinuke_role_whitelist (
            guild_id    INTEGER,
            role_id     INTEGER,
            PRIMARY KEY (guild_id, role_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS antinuke_event_whitelist (
            guild_id    INTEGER,
            user_id     INTEGER,
            events      TEXT DEFAULT '[]',
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    # ── Anti-Spam & Automod ──────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS antispam (
            guild_id    INTEGER PRIMARY KEY,
            enabled     INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS automod (
            guild_id    INTEGER PRIMARY KEY,
            settings    TEXT DEFAULT '{}',
            punishment  TEXT DEFAULT '{}',
            wl_roles    TEXT DEFAULT '[]',
            timeouts    TEXT DEFAULT '{}',
            log_channel INTEGER DEFAULT 0
        )
    """)

    # ── Bot Admins ──────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS bot_admins (
            guild_id    INTEGER,
            user_id     INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    # ── Warnings ────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER,
            user_id     INTEGER,
            reason      TEXT,
            mod_id      INTEGER,
            timestamp   TEXT
        )
    """)

    # ── Notes ───────────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER,
            user_id     INTEGER,
            text        TEXT,
            mod_id      INTEGER,
            timestamp   TEXT
        )
    """)

    # ── Ticket Config ────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS ticket_config (
            guild_id        INTEGER PRIMARY KEY,
            ping_role       INTEGER DEFAULT 0,
            close_dm        TEXT    DEFAULT '',
            panel_title     TEXT    DEFAULT '',
            panel_desc      TEXT    DEFAULT '',
            panel_rules     TEXT    DEFAULT '[]',
            support_hours   TEXT    DEFAULT '',
            footer          TEXT    DEFAULT '',
            category_map    TEXT    DEFAULT '{}',
            ticket_cats     TEXT    DEFAULT '',
            max_tickets     INTEGER DEFAULT 1,
            min_account_age INTEGER DEFAULT 0,
            require_reason  INTEGER DEFAULT 0
        )
    """)
    # Add ticket_cats column if it doesn't exist (migration)
    try:
        c.execute("ALTER TABLE ticket_config ADD COLUMN ticket_cats TEXT DEFAULT ''")
    except:
        pass  # Column already exists
    # Add new security columns if missing (migration)
    for col, default in [("max_tickets", "1"), ("min_account_age", "0"), ("require_reason", "0")]:
        try:
            c.execute(f"ALTER TABLE ticket_config ADD COLUMN {col} INTEGER DEFAULT {default}")
        except:
            pass
    # Ticket blacklist table
    c.execute("""
        CREATE TABLE IF NOT EXISTS ticket_blacklist (
            guild_id    INTEGER,
            user_id     INTEGER,
            reason      TEXT    DEFAULT '',
            mod_id      INTEGER DEFAULT 0,
            timestamp   TEXT    DEFAULT '',
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    # ── Verification ─────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS verify_config (
            guild_id        INTEGER PRIMARY KEY,
            enabled         INTEGER DEFAULT 0,
            verified_role   INTEGER DEFAULT 0,
            unverified_role INTEGER DEFAULT 0,
            verify_channel  INTEGER DEFAULT 0,
            log_channel     INTEGER DEFAULT 0,
            msg_id          INTEGER DEFAULT 0
        )
    """)

    # ── Admin / Pricing tables ──────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS pricing_plans (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            price       TEXT    NOT NULL,
            duration    TEXT    DEFAULT 'Monthly',
            description TEXT    DEFAULT '',
            features    TEXT    DEFAULT '[]',
            badge       TEXT    DEFAULT '',
            color       TEXT    DEFAULT '#5865f2',
            active      INTEGER DEFAULT 1,
            position    INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        TEXT DEFAULT '',
            username       TEXT DEFAULT '',
            plan_name      TEXT NOT NULL,
            amount         TEXT NOT NULL,
            status         TEXT DEFAULT 'pending',
            payment_method TEXT DEFAULT '',
            discord_id     TEXT DEFAULT '',
            server_id      TEXT DEFAULT '',
            note           TEXT DEFAULT '',
            created_at     TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS site_config (
            key   TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
    """)
    # Seed default plans
    if c.execute("SELECT COUNT(*) FROM pricing_plans").fetchone()[0] == 0:
        import json as _json
        c.executemany(
            "INSERT INTO pricing_plans (name,price,duration,description,features,badge,color,active,position) VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("Basic",   "Rs.99",  "Monthly", "Perfect for small servers",       _json.dumps(["Anti-Nuke","Automod","Tickets","Music","Dashboard Access"]),        "Bronze", "#57f287", 1, 1),
                ("Pro",     "Rs.199", "Monthly", "Best for growing communities",    _json.dumps(["Everything in Basic","Priority Support","Advanced Logs","Custom Welcome","Whitelist 10 Users"]), "Silver", "#5865f2", 1, 2),
                ("Premium", "Rs.399", "Monthly", "For large servers & communities", _json.dumps(["Everything in Pro","24/7 VIP Support","Custom Bot Name","Unlimited Whitelist","Early Access"]), "Gold",   "#fee75c", 1, 3),
            ]
        )
    # Join messages
    c.execute("""
        CREATE TABLE IF NOT EXISTS welcome_join (
            guild_id    INTEGER PRIMARY KEY,
            enabled     INTEGER DEFAULT 0,
            channel_id  INTEGER DEFAULT 0,
            title       TEXT    DEFAULT 'Welcome to {server}!',
            description TEXT    DEFAULT 'Hey {mention}, welcome to **{server}**!\nYou are member **#{count}**.',
            color       TEXT    DEFAULT '#57f287',
            thumbnail   TEXT    DEFAULT 'member',
            image_url   TEXT    DEFAULT '',
            footer_text TEXT    DEFAULT 'Empire Bot',
            show_fields INTEGER DEFAULT 1
        )
    """)
    # Leave messages
    c.execute("""
        CREATE TABLE IF NOT EXISTS welcome_leave (
            guild_id    INTEGER PRIMARY KEY,
            enabled     INTEGER DEFAULT 0,
            channel_id  INTEGER DEFAULT 0,
            title       TEXT    DEFAULT '{user} has left.',
            description TEXT    DEFAULT '**{user}** just left the server.\nWe now have **{count}** members.',
            color       TEXT    DEFAULT '#ed4245',
            thumbnail   TEXT    DEFAULT 'member',
            image_url   TEXT    DEFAULT '',
            footer_text TEXT    DEFAULT 'Empire Bot',
            show_fields INTEGER DEFAULT 0
        )
    """)
    # Boost messages
    c.execute("""
        CREATE TABLE IF NOT EXISTS welcome_boost (
            guild_id    INTEGER PRIMARY KEY,
            enabled     INTEGER DEFAULT 0,
            channel_id  INTEGER DEFAULT 0,
            title       TEXT    DEFAULT '🚀 New Boost!',
            description TEXT    DEFAULT 'Thank you {mention} for boosting **{server}**!\nWe now have **{boost_count}** boosts!',
            color       TEXT    DEFAULT '#f47fff',
            thumbnail   TEXT    DEFAULT 'member',
            image_url   TEXT    DEFAULT '',
            footer_text TEXT    DEFAULT 'Empire Bot',
            show_fields INTEGER DEFAULT 1
        )
    """)

    # ── Sync Log — Dashboard changes yahan likhta hai, bot yahan se padhta hai ──
    c.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id    INTEGER NOT NULL,
            change_type TEXT    NOT NULL,
            changed_at  TEXT    DEFAULT (datetime('now')),
            processed   INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized — {DB_PATH}")


# ═══════════════════════════════════════════════════════════════════════════════
#  GUILD SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_guild(conn, guild_id: int):
    conn.execute(
        "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,))

def get_guild(guild_id: int) -> dict:
    conn = get_conn()
    _ensure_guild(conn, guild_id)
    conn.commit()
    row = conn.execute(
        "SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def set_prefix(guild_id: int, prefix: str):
    conn = get_conn()
    _ensure_guild(conn, guild_id)
    conn.execute("UPDATE guild_settings SET prefix=? WHERE guild_id=?", (prefix, guild_id))
    conn.commit(); conn.close()

def set_log_channel(guild_id: int, log_type: str, channel_id: int):
    """log_type: 'bot_log' | 'mod_log' | 'invite_log' | 'ticket_log'"""
    conn = get_conn()
    _ensure_guild(conn, guild_id)
    conn.execute(f"UPDATE guild_settings SET {log_type}=? WHERE guild_id=?", (channel_id, guild_id))
    conn.commit(); conn.close()

def load_all_prefixes() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT guild_id, prefix FROM guild_settings").fetchall()
    conn.close()
    return {r["guild_id"]: r["prefix"] for r in rows}

def load_all_logs() -> dict:
    """Returns {guild_id: {bot_log, mod_log, invite_log, ticket_log}}"""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM guild_settings").fetchall()
    conn.close()
    return {r["guild_id"]: dict(r) for r in rows}


# ═══════════════════════════════════════════════════════════════════════════════
#  ANTI-NUKE
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_antinuke(conn, guild_id: int):
    conn.execute("INSERT OR IGNORE INTO antinuke (guild_id) VALUES (?)", (guild_id,))

def get_antinuke(guild_id: int) -> dict:
    conn = get_conn()
    _ensure_antinuke(conn, guild_id)
    conn.commit()
    row = conn.execute("SELECT * FROM antinuke WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def set_antinuke(guild_id: int, **kwargs):
    conn = get_conn()
    _ensure_antinuke(conn, guild_id)
    for k, v in kwargs.items():
        conn.execute(f"UPDATE antinuke SET {k}=? WHERE guild_id=?", (v, guild_id))
    conn.commit(); conn.close()

def load_all_antinuke() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM antinuke").fetchall()
    conn.close()
    return {r["guild_id"]: dict(r) for r in rows}

# Whitelist
def wl_add_user(guild_id: int, user_id: int):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO antinuke_whitelist VALUES (?,?)", (guild_id, user_id))
    conn.commit(); conn.close()

def wl_remove_user(guild_id: int, user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM antinuke_whitelist WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit(); conn.close()

def wl_get_users(guild_id: int) -> set:
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM antinuke_whitelist WHERE guild_id=?", (guild_id,)).fetchall()
    conn.close()
    return {r["user_id"] for r in rows}

def wl_add_role(guild_id: int, role_id: int):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO antinuke_role_whitelist VALUES (?,?)", (guild_id, role_id))
    conn.commit(); conn.close()

def wl_remove_role(guild_id: int, role_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM antinuke_role_whitelist WHERE guild_id=? AND role_id=?", (guild_id, role_id))
    conn.commit(); conn.close()

def wl_get_roles(guild_id: int) -> set:
    conn = get_conn()
    rows = conn.execute("SELECT role_id FROM antinuke_role_whitelist WHERE guild_id=?", (guild_id,)).fetchall()
    conn.close()
    return {r["role_id"] for r in rows}

def load_all_whitelists() -> tuple:
    """Returns (user_wl: {gid: set}, role_wl: {gid: set})"""
    conn = get_conn()
    u_rows = conn.execute("SELECT * FROM antinuke_whitelist").fetchall()
    r_rows = conn.execute("SELECT * FROM antinuke_role_whitelist").fetchall()
    ev_rows = conn.execute("SELECT * FROM antinuke_event_whitelist").fetchall()
    conn.close()

    user_wl = {}
    for r in u_rows:
        user_wl.setdefault(r["guild_id"], set()).add(r["user_id"])

    role_wl = {}
    for r in r_rows:
        role_wl.setdefault(r["guild_id"], set()).add(r["role_id"])

    ev_wl = {}
    for r in ev_rows:
        ev_wl.setdefault(r["guild_id"], {})[r["user_id"]] = set(json.loads(r["events"]))

    return user_wl, role_wl, ev_wl

def ev_wl_save(guild_id: int, user_id: int, events: set):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO antinuke_event_whitelist (guild_id, user_id, events) VALUES (?,?,?)",
        (guild_id, user_id, json.dumps(list(events))))
    conn.commit(); conn.close()

def ev_wl_remove(guild_id: int, user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM antinuke_event_whitelist WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit(); conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  ANTI-SPAM & AUTOMOD
# ═══════════════════════════════════════════════════════════════════════════════

def get_antispam(guild_id: int) -> bool:
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO antispam (guild_id) VALUES (?)", (guild_id,))
    conn.commit()
    row = conn.execute("SELECT enabled FROM antispam WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return bool(row["enabled"]) if row else False

def set_antispam(guild_id: int, enabled: bool):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO antispam (guild_id, enabled) VALUES (?,?)", (guild_id, int(enabled)))
    conn.commit(); conn.close()

def load_all_antispam() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM antispam").fetchall()
    conn.close()
    return {r["guild_id"]: bool(r["enabled"]) for r in rows}

def _ensure_automod(conn, guild_id: int):
    conn.execute("INSERT OR IGNORE INTO automod (guild_id) VALUES (?)", (guild_id,))

def get_automod(guild_id: int) -> dict:
    conn = get_conn()
    _ensure_automod(conn, guild_id)
    conn.commit()
    row = conn.execute("SELECT * FROM automod WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    if not row: return {}
    return {
        "settings":    json.loads(row["settings"]),
        "punishment":  json.loads(row["punishment"]),
        "wl_roles":    set(json.loads(row["wl_roles"])),
        "timeouts":    json.loads(row["timeouts"]),
        "log_channel": row["log_channel"],
    }

def save_automod_settings(guild_id: int, settings: dict):
    conn = get_conn()
    _ensure_automod(conn, guild_id)
    conn.execute("UPDATE automod SET settings=? WHERE guild_id=?",
                 (json.dumps(settings), guild_id))
    conn.commit(); conn.close()

def save_automod_punishment(guild_id: int, punishment: dict):
    conn = get_conn()
    _ensure_automod(conn, guild_id)
    conn.execute("UPDATE automod SET punishment=? WHERE guild_id=?",
                 (json.dumps(punishment), guild_id))
    conn.commit(); conn.close()

def save_automod_wl_roles(guild_id: int, roles: set):
    conn = get_conn()
    _ensure_automod(conn, guild_id)
    conn.execute("UPDATE automod SET wl_roles=? WHERE guild_id=?",
                 (json.dumps(list(roles)), guild_id))
    conn.commit(); conn.close()

def save_automod_timeouts(guild_id: int, timeouts: dict):
    conn = get_conn()
    _ensure_automod(conn, guild_id)
    conn.execute("UPDATE automod SET timeouts=? WHERE guild_id=?",
                 (json.dumps(timeouts), guild_id))
    conn.commit(); conn.close()

def set_automod_log(guild_id: int, channel_id: int):
    conn = get_conn()
    _ensure_automod(conn, guild_id)
    conn.execute("UPDATE automod SET log_channel=? WHERE guild_id=?", (channel_id, guild_id))
    conn.commit(); conn.close()

def load_all_automod() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM automod").fetchall()
    conn.close()
    result = {}
    for r in rows:
        result[r["guild_id"]] = {
            "settings":    json.loads(r["settings"]),
            "punishment":  json.loads(r["punishment"]),
            "wl_roles":    set(json.loads(r["wl_roles"])),
            "timeouts":    json.loads(r["timeouts"]),
            "log_channel": r["log_channel"],
        }
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  BOT ADMINS
# ═══════════════════════════════════════════════════════════════════════════════

def admin_add(guild_id: int, user_id: int):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO bot_admins VALUES (?,?)", (guild_id, user_id))
    conn.commit(); conn.close()

def admin_remove(guild_id: int, user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM bot_admins WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit(); conn.close()

def admin_get(guild_id: int) -> set:
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM bot_admins WHERE guild_id=?", (guild_id,)).fetchall()
    conn.close()
    return {r["user_id"] for r in rows}

def load_all_admins() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bot_admins").fetchall()
    conn.close()
    result = {}
    for r in rows:
        result.setdefault(r["guild_id"], set()).add(r["user_id"])
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  WARNINGS & NOTES
# ═══════════════════════════════════════════════════════════════════════════════

def warn_add(guild_id: int, user_id: int, reason: str, mod_id: int):
    ts = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO warnings (guild_id, user_id, reason, mod_id, timestamp) VALUES (?,?,?,?,?)",
        (guild_id, user_id, reason, mod_id, ts))
    conn.commit(); conn.close()

def warn_get(guild_id: int, user_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id",
        (guild_id, user_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def warn_clear(guild_id: int, user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit(); conn.close()

def warn_remove_one(guild_id: int, user_id: int, index: int) -> bool:
    """Remove warning by 1-based index. Returns True if removed."""
    warns = warn_get(guild_id, user_id)
    if index < 1 or index > len(warns):
        return False
    wid = warns[index-1]["id"]
    conn = get_conn()
    conn.execute("DELETE FROM warnings WHERE id=?", (wid,))
    conn.commit(); conn.close()
    return True

def note_add(guild_id: int, user_id: int, text: str, mod_id: int):
    ts = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT INTO notes (guild_id, user_id, text, mod_id, timestamp) VALUES (?,?,?,?,?)",
        (guild_id, user_id, text, mod_id, ts))
    conn.commit(); conn.close()

def note_get(guild_id: int, user_id: int) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notes WHERE guild_id=? AND user_id=? ORDER BY id",
        (guild_id, user_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def note_clear(guild_id: int, user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM notes WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit(); conn.close()

def load_all_warns() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM warnings ORDER BY id").fetchall()
    conn.close()
    result = {}
    for r in rows:
        key = (r["guild_id"], r["user_id"])
        result.setdefault(key, []).append(dict(r))
    return result

def load_all_notes() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM notes ORDER BY id").fetchall()
    conn.close()
    result = {}
    for r in rows:
        key = (r["guild_id"], r["user_id"])
        result.setdefault(key, []).append(dict(r))
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  TICKET CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_ticket(conn, guild_id: int):
    conn.execute("INSERT OR IGNORE INTO ticket_config (guild_id) VALUES (?)", (guild_id,))

def get_ticket_config(guild_id: int) -> dict:
    conn = get_conn()
    _ensure_ticket(conn, guild_id)
    conn.commit()
    row = conn.execute("SELECT * FROM ticket_config WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    if not row: return {}
    d = dict(row)
    d["panel_rules"]  = json.loads(d["panel_rules"])
    d["category_map"] = json.loads(d["category_map"])
    return d

def save_ticket_config(guild_id: int, **kwargs):
    conn = get_conn()
    _ensure_ticket(conn, guild_id)
    for k, v in kwargs.items():
        if isinstance(v, (list, dict)):
            v = json.dumps(v)
        conn.execute(f"UPDATE ticket_config SET {k}=? WHERE guild_id=?", (v, guild_id))
    conn.commit(); conn.close()

def load_all_ticket_configs() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM ticket_config").fetchall()
    conn.close()
    result = {}
    for r in rows:
        d = dict(r)
        d["panel_rules"]  = json.loads(d["panel_rules"])
        d["category_map"] = json.loads(d["category_map"])
        result[r["guild_id"]] = d
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  VERIFICATION CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_verify(conn, guild_id: int):
    conn.execute("INSERT OR IGNORE INTO verify_config (guild_id) VALUES (?)", (guild_id,))

def get_verify_config(guild_id: int) -> dict:
    conn = get_conn()
    _ensure_verify(conn, guild_id)
    conn.commit()
    row = conn.execute("SELECT * FROM verify_config WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def save_verify_config(guild_id: int, **kwargs):
    conn = get_conn()
    _ensure_verify(conn, guild_id)
    for k, v in kwargs.items():
        conn.execute(f"UPDATE verify_config SET {k}=? WHERE guild_id=?", (v, guild_id))
    conn.commit(); conn.close()

def load_all_verify_configs() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM verify_config").fetchall()
    conn.close()
    return {r["guild_id"]: dict(r) for r in rows}


# ═══════════════════════════════════════════════════════════════════════════════
#  PRICING & ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

def get_plans(active_only=True):
    conn = get_conn()
    if active_only:
        rows = conn.execute("SELECT * FROM pricing_plans WHERE active=1 ORDER BY position").fetchall()
    else:
        rows = conn.execute("SELECT * FROM pricing_plans ORDER BY position").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        import json
        d['features'] = json.loads(d['features']) if d.get('features') else []
        result.append(d)
    return result

def save_plan(data: dict):
    import json
    conn = get_conn()
    if data.get('id'):
        conn.execute("""UPDATE pricing_plans SET name=?,price=?,duration=?,description=?,
            features=?,badge=?,color=?,active=?,position=? WHERE id=?""",
            (data['name'], data['price'], data['duration'], data['description'],
             json.dumps(data.get('features',[])), data.get('badge',''), data.get('color','#5865f2'),
             int(data.get('active',1)), int(data.get('position',0)), data['id']))
    else:
        conn.execute("""INSERT INTO pricing_plans (name,price,duration,description,features,badge,color,active,position)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (data['name'], data['price'], data['duration'], data['description'],
             json.dumps(data.get('features',[])), data.get('badge',''), data.get('color','#5865f2'),
             int(data.get('active',1)), int(data.get('position',0))))
    conn.commit(); conn.close()

def delete_plan(plan_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM pricing_plans WHERE id=?", (plan_id,))
    conn.commit(); conn.close()

def get_orders(status=None, limit=50):
    conn = get_conn()
    if status:
        rows = conn.execute("SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_order(data: dict):
    conn = get_conn()
    conn.execute("""INSERT INTO orders (user_id,username,plan_name,amount,status,payment_method,discord_id,server_id,note)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (data.get('user_id',''), data.get('username',''), data.get('plan_name',''),
         data.get('amount',''), data.get('status','pending'), data.get('payment_method',''),
         data.get('discord_id',''), data.get('server_id',''), data.get('note','')))
    conn.commit(); conn.close()

def update_order_status(order_id: int, status: str):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit(); conn.close()

def delete_order(order_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
    conn.commit(); conn.close()

def get_site_config(key: str, default='') -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM site_config WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_site_config(key: str, value: str):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO site_config (key,value) VALUES (?,?)", (key, value))
    conn.commit(); conn.close()

def get_stats():
    conn = get_conn()
    total_guilds   = conn.execute("SELECT COUNT(*) FROM guild_settings").fetchone()[0]
    total_orders   = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    paid_orders    = conn.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
    conn.close()
    return {'guilds': total_guilds, 'total_orders': total_orders,
            'pending': pending_orders, 'paid': paid_orders}


# ═══════════════════════════════════════════════════════════════════════════════
#  WELCOME / LEAVE / BOOST MESSAGES
# ═══════════════════════════════════════════════════════════════════════════════

_WELCOME_DEFAULTS = {
    'join':  {'enabled':0,'channel_id':0,'title':'Welcome to {server}!','description':'Hey {mention}, welcome to **{server}**!\nYou are member **#{count}**.','color':'#57f287','thumbnail':'member','image_url':'','footer_text':'Empire Bot','show_fields':1},
    'leave': {'enabled':0,'channel_id':0,'title':'{user} has left.','description':'**{user}** just left the server.\nWe now have **{count}** members.','color':'#ed4245','thumbnail':'member','image_url':'','footer_text':'Empire Bot','show_fields':0},
    'boost': {'enabled':0,'channel_id':0,'title':'🚀 New Boost!','description':'Thank you {mention} for boosting **{server}**!\nWe now have **{boost_count}** boosts!','color':'#f47fff','thumbnail':'member','image_url':'','footer_text':'Empire Bot','show_fields':1},
}

def get_welcome(guild_id: int, msg_type: str = 'join') -> dict:
    table = f'welcome_{msg_type}'
    conn = get_conn()
    try:
        row = conn.execute(f"SELECT * FROM {table} WHERE guild_id=?", (guild_id,)).fetchone()
    except Exception:
        row = None
    conn.close()
    if row:
        d = dict(row)
        d.setdefault('show_fields', 1)
        return d
    default = dict(_WELCOME_DEFAULTS.get(msg_type, _WELCOME_DEFAULTS['join']))
    default['guild_id'] = guild_id
    return default

def save_welcome(guild_id: int, msg_type: str = 'join', **kwargs):
    table = f'welcome_{msg_type}'
    conn = get_conn()
    try:
        conn.execute(f"INSERT OR IGNORE INTO {table} (guild_id) VALUES (?)", (guild_id,))
        for key, val in kwargs.items():
            try:
                conn.execute(f"UPDATE {table} SET {key}=? WHERE guild_id=?", (val, guild_id))
            except Exception:
                pass
        conn.commit()
    except Exception:
        pass
    conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
#  TICKET BLACKLIST
# ═══════════════════════════════════════════════════════════════════════════════

def add_ticket_blacklist(guild_id: int, user_id: int, reason: str = '', mod_id: int = 0) -> None:
    from datetime import datetime, timezone
    conn = get_conn()
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    conn.execute(
        "INSERT OR REPLACE INTO ticket_blacklist (guild_id, user_id, reason, mod_id, timestamp) VALUES (?,?,?,?,?)",
        (guild_id, user_id, reason, mod_id, ts)
    )
    conn.commit(); conn.close()

def remove_ticket_blacklist(guild_id: int, user_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM ticket_blacklist WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    affected = cur.rowcount
    conn.commit(); conn.close()
    return affected > 0

def is_ticket_blacklisted(guild_id: int, user_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM ticket_blacklist WHERE guild_id=? AND user_id=?", (guild_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_ticket_blacklist(guild_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM ticket_blacklist WHERE guild_id=?", (guild_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════════════════
#  PREMIUM SYSTEM — Added by Empire Premium
# ═══════════════════════════════════════════════════════════════════════════════

def _ensure_premium_tables():
    conn = get_conn()
    c = conn.cursor()

    # Premium servers table
    c.execute("""
        CREATE TABLE IF NOT EXISTS premium_servers (
            guild_id    INTEGER PRIMARY KEY,
            plan_name   TEXT    DEFAULT 'Premium',
            activated_by TEXT   DEFAULT '',
            activated_at TEXT   DEFAULT '',
            expires_at  TEXT    DEFAULT '',
            active      INTEGER DEFAULT 1
        )
    """)

    # Premium config key-value store per guild
    c.execute("""
        CREATE TABLE IF NOT EXISTS premium_config (
            guild_id    INTEGER,
            key         TEXT,
            value       TEXT,
            PRIMARY KEY (guild_id, key)
        )
    """)

    # Level / XP table
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_levels (
            guild_id    INTEGER,
            user_id     INTEGER,
            xp          INTEGER DEFAULT 0,
            level       INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        )
    """)

    # Server Backups table — backup_id se cross-server import support
    c.execute("""
        CREATE TABLE IF NOT EXISTS server_backups (
            backup_id   TEXT    PRIMARY KEY,
            guild_id    INTEGER NOT NULL,
            guild_name  TEXT    DEFAULT '',
            owner_id    INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT '',
            roles_count INTEGER DEFAULT 0,
            channels_count INTEGER DEFAULT 0,
            data        TEXT    DEFAULT '{}'
        )
    """)

    conn.commit()
    conn.close()

_ensure_premium_tables()


def is_premium_server(guild_id: int) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT active FROM premium_servers WHERE guild_id=? AND active=1", (guild_id,)
    ).fetchone()
    conn.close()
    return bool(row)


def activate_premium(guild_id: int, plan_name: str, activated_by: str, expires_at: str = '') -> None:
    from datetime import datetime, timezone
    conn = get_conn()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    conn.execute(
        """INSERT OR REPLACE INTO premium_servers
           (guild_id, plan_name, activated_by, activated_at, expires_at, active)
           VALUES (?,?,?,?,?,1)""",
        (guild_id, plan_name, activated_by, now, expires_at)
    )
    conn.commit(); conn.close()


def deactivate_premium(guild_id: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE premium_servers SET active=0 WHERE guild_id=?", (guild_id,))
    conn.commit(); conn.close()


def get_all_premium_servers() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM premium_servers WHERE active=1").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_premium_server(guild_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM premium_servers WHERE guild_id=?", (guild_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_premium_config(guild_id: int, key: str, value) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO premium_config (guild_id, key, value) VALUES (?,?,?)",
        (guild_id, key, str(value))
    )
    conn.commit(); conn.close()


def get_premium_config(guild_id: int, key: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT value FROM premium_config WHERE guild_id=? AND key=?", (guild_id, key)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def load_all_premium_configs() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT guild_id, key, value FROM premium_config").fetchall()
    conn.close()
    result = {}
    for row in rows:
        gid = row[0]
        if gid not in result:
            result[gid] = {}
        result[gid][row[1]] = row[2]
    return result


def set_user_level(guild_id: int, user_id: int, xp: int, level: int) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO user_levels (guild_id, user_id, xp, level) VALUES (?,?,?,?)",
        (guild_id, user_id, xp, level)
    )
    conn.commit(); conn.close()


def get_user_level(guild_id: int, user_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT xp, level FROM user_levels WHERE guild_id=? AND user_id=?", (guild_id, user_id)
    ).fetchone()
    conn.close()
    return {"xp": row[0], "level": row[1]} if row else {"xp": 0, "level": 0}


def get_guild_leaderboard(guild_id: int, limit: int = 10) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_id, xp, level FROM user_levels WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT ?",
        (guild_id, limit)
    ).fetchall()
    conn.close()
    return [{"user_id": r[0], "xp": r[1], "level": r[2]} for r in rows]


# ─── Guild Name Cache (for dashboard display) ────────────────────────────────

def _ensure_guild_name_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guild_names (
            guild_id  INTEGER PRIMARY KEY,
            name      TEXT    DEFAULT '',
            icon      TEXT    DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

_ensure_guild_name_table()

def save_guild_name(guild_id: int, name: str, icon: str = '') -> None:
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO guild_names (guild_id, name, icon) VALUES (?,?,?)",
        (guild_id, name, icon or '')
    )
    conn.commit()
    conn.close()

def get_guild_name(guild_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT name, icon FROM guild_names WHERE guild_id=?", (guild_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}

def get_all_guild_names() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT guild_id, name, icon FROM guild_names").fetchall()
    conn.close()
    return {str(r[0]): {"id": str(r[0]), "name": r[1], "icon": r[2]} for r in rows}


# ══════════════════════════════════════════════════════
#  SERVER BACKUP — backup_id ke saath save/load
# ══════════════════════════════════════════════════════

def save_server_backup(backup_id: str, guild_id: int, guild_name: str, owner_id: int,
                       created_at: str, roles_count: int, channels_count: int, data: str) -> None:
    """Save a server backup with a unique backup_id."""
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO server_backups
           (backup_id, guild_id, guild_name, owner_id, created_at, roles_count, channels_count, data)
           VALUES (?,?,?,?,?,?,?,?)""",
        (backup_id, guild_id, guild_name, owner_id, created_at, roles_count, channels_count, data)
    )
    conn.commit()
    conn.close()


def get_backup_by_id(backup_id: str) -> dict | None:
    """Get a backup by its unique backup_id."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM server_backups WHERE backup_id=?", (backup_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_backups_by_guild(guild_id: int) -> list:
    """Get all backups created by a specific guild."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT backup_id, guild_name, created_at, roles_count, channels_count FROM server_backups WHERE guild_id=? ORDER BY created_at DESC",
        (guild_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_backup(backup_id: str) -> None:
    """Delete a backup by ID."""
    conn = get_conn()
    conn.execute("DELETE FROM server_backups WHERE backup_id=?", (backup_id,))
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════
#  GIVEAWAY PERSISTENCE — survive bot restart
# ══════════════════════════════════════════════════════

def _ensure_giveaway_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS active_giveaways (
            msg_id      INTEGER PRIMARY KEY,
            channel_id  INTEGER NOT NULL,
            guild_id    INTEGER NOT NULL,
            prize       TEXT NOT NULL,
            winners     INTEGER NOT NULL,
            end_time    TEXT NOT NULL,
            host_id     INTEGER NOT NULL,
            ended       INTEGER DEFAULT 0
        )
    """)
    conn.commit(); conn.close()

_ensure_giveaway_table()

def save_giveaway(msg_id: int, channel_id: int, guild_id: int, prize: str, winners: int, end_time: str, host_id: int):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO active_giveaways
           (msg_id, channel_id, guild_id, prize, winners, end_time, host_id, ended)
           VALUES (?,?,?,?,?,?,?,0)""",
        (msg_id, channel_id, guild_id, prize, winners, end_time, host_id)
    )
    conn.commit(); conn.close()

def end_giveaway_db(msg_id: int):
    conn = get_conn()
    conn.execute("UPDATE active_giveaways SET ended=1 WHERE msg_id=?", (msg_id,))
    conn.commit(); conn.close()

def get_active_giveaways() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM active_giveaways WHERE ended=0").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_giveaway(msg_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM active_giveaways WHERE msg_id=?", (msg_id,))
    conn.commit(); conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  SYNC LOG — Dashboard → Bot auto-sync system
#  Dashboard koi bhi setting save kare → sync_log mein entry daale
#  Bot har 10s mein check kare → naye entries pe settings reload kare
# ══════════════════════════════════════════════════════════════════════════════

def push_sync(guild_id: int, change_type: str) -> None:
    """Dashboard yeh call kare jab bhi koi setting save ho."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO sync_log (guild_id, change_type) VALUES (?,?)",
        (guild_id, change_type)
    )
    conn.commit(); conn.close()


def get_pending_syncs() -> list:
    """Bot yeh call kare — sab unprocessed sync entries return karta hai."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, guild_id, change_type FROM sync_log WHERE processed=0 ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_syncs_done(ids: list) -> None:
    """Bot processed entries ko done mark kare."""
    if not ids:
        return
    conn = get_conn()
    placeholders = ",".join("?" * len(ids))
    conn.execute(f"UPDATE sync_log SET processed=1 WHERE id IN ({placeholders})", ids)
    # Purani processed entries cleanup (sirf last 500 rakho)
    conn.execute("DELETE FROM sync_log WHERE processed=1 AND id NOT IN (SELECT id FROM sync_log ORDER BY id DESC LIMIT 500)")
    conn.commit(); conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  INVITE TRACKER — Persistent invite stats (survives bot restarts)
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_invite_tables():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS invite_stats (
            guild_id  INTEGER NOT NULL,
            user_id   INTEGER NOT NULL,
            invites   INTEGER DEFAULT 0,
            left      INTEGER DEFAULT 0,
            fake      INTEGER DEFAULT 0,
            rejoins   INTEGER DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS invite_member_map (
            guild_id   INTEGER NOT NULL,
            member_id  INTEGER NOT NULL,
            inviter_id INTEGER NOT NULL,
            join_type  TEXT    DEFAULT 'real',
            PRIMARY KEY (guild_id, member_id)
        );
    """)
    conn.commit()
    conn.close()

_ensure_invite_tables()


def invite_get(guild_id: int, user_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT invites, left, fake, rejoins FROM invite_stats WHERE guild_id=? AND user_id=?",
        (guild_id, user_id)
    ).fetchone()
    conn.close()
    if row:
        return {"invites": row[0], "left": row[1], "fake": row[2], "rejoins": row[3]}
    return {"invites": 0, "left": 0, "fake": 0, "rejoins": 0}


def invite_set(guild_id: int, user_id: int, data: dict) -> None:
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO invite_stats (guild_id, user_id, invites, left, fake, rejoins)
           VALUES (?,?,?,?,?,?)""",
        (guild_id, user_id, data.get("invites", 0), data.get("left", 0),
         data.get("fake", 0), data.get("rejoins", 0))
    )
    conn.commit()
    conn.close()


def invite_update(guild_id: int, user_id: int, **kwargs) -> dict:
    """Atomically update specific fields. Returns new data."""
    data = invite_get(guild_id, user_id)
    for k, v in kwargs.items():
        if k in data:
            data[k] = max(0, data[k] + v)
    invite_set(guild_id, user_id, data)
    return data


def invite_reset(guild_id: int, user_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM invite_stats WHERE guild_id=? AND user_id=?", (guild_id, user_id))
    conn.commit()
    conn.close()


def invite_get_all(guild_id: int) -> list:
    """Get all invite stats for a guild sorted by invites desc."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_id, invites, left, fake, rejoins FROM invite_stats WHERE guild_id=? ORDER BY invites DESC",
        (guild_id,)
    ).fetchall()
    conn.close()
    return [{"user_id": r[0], "invites": r[1], "left": r[2], "fake": r[3], "rejoins": r[4]} for r in rows]


def invmap_get(guild_id: int, member_id: int) -> tuple:
    """Returns (inviter_id, join_type) or (None, None)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT inviter_id, join_type FROM invite_member_map WHERE guild_id=? AND member_id=?",
        (guild_id, member_id)
    ).fetchone()
    conn.close()
    return (row[0], row[1]) if row else (None, None)


def invmap_set(guild_id: int, member_id: int, inviter_id: int, join_type: str = "real") -> None:
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO invite_member_map (guild_id, member_id, inviter_id, join_type)
           VALUES (?,?,?,?)""",
        (guild_id, member_id, inviter_id, join_type)
    )
    conn.commit()
    conn.close()


def invmap_delete(guild_id: int, member_id: int) -> None:
    conn = get_conn()
    conn.execute(
        "DELETE FROM invite_member_map WHERE guild_id=? AND member_id=?",
        (guild_id, member_id)
    )
    conn.commit()
    conn.close()
