# ╔══════════════════════════════════════════════════════════════════════╗
# ║  EMPIRE SYNC API — Dashboard ↔ Bot Auto-Sync Bridge                ║
# ║                                                                      ║
# ║  Kaam kaise karta hai:                                               ║
# ║  1. Dashboard koi bhi setting save kare                              ║
# ║  2. `notify_bot(guild_id, change_type)` call karo                   ║
# ║  3. Bot 10 seconds mein automatically reload kar leta hai            ║
# ║                                                                      ║
# ║  Koi command nahi, koi restart nahi, koi manual kaam nahi!          ║
# ╚══════════════════════════════════════════════════════════════════════╝

import os
import sys

# Load .env from same folder
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except Exception:
    pass

# Always use same db.py as bot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db as DB

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN FUNCTION — Dashboard is file se yeh function import kare
# ══════════════════════════════════════════════════════════════════════════════

# Valid change types — dashboard in mein se koi bhi pass kare
CHANGE_TYPES = {
    "all",          # Sab settings reload
    "settings",     # Prefix, log channels
    "antinuke",     # Anti-nuke + whitelists
    "antispam",     # Anti-spam
    "automod",      # Automod settings
    "admins",       # Bot admins
    "verify",       # Verification config
    "premium",      # Premium status
    "welcome",      # Welcome/leave messages
}


def notify_bot(guild_id: int, change_type: str = "all") -> bool:
    """
    Dashboard is function ko call kare jab bhi koi setting save ho.

    Args:
        guild_id:    Discord server ID (integer)
        change_type: Kya change hua — "all", "antinuke", "automod", etc.

    Returns:
        True agar successfully DB mein log hua, False agar error

    Example:
        from sync_api import notify_bot
        notify_bot(123456789, "antinuke")   # antinuke change hua
        notify_bot(123456789, "all")         # sab reload karo
    """
    if change_type not in CHANGE_TYPES:
        change_type = "all"  # Unknown type → sab reload karo
    try:
        DB.push_sync(int(guild_id), change_type)
        print(f"[SYNC] Queued reload: guild={guild_id} type={change_type}")
        return True
    except Exception as e:
        print(f"[SYNC] Failed to queue reload: {e}")
        return False


def notify_bot_multi(guild_id: int, change_types: list) -> bool:
    """
    Multiple change types ek saath queue karo.

    Example:
        notify_bot_multi(123456789, ["antinuke", "automod"])
    """
    try:
        for ctype in change_types:
            DB.push_sync(int(guild_id), ctype if ctype in CHANGE_TYPES else "all")
        return True
    except Exception as e:
        print(f"[SYNC] Failed to queue multi-reload: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD KE HAR SAVE FUNCTION MEIN USE KARO — EXAMPLES
# ══════════════════════════════════════════════════════════════════════════════
#
#  ── Anti-Nuke save ke baad ────────────────────────────────────────────────
#  DB.set_antinuke(guild_id, enabled=1, punishment="ban")
#  notify_bot(guild_id, "antinuke")   ← yeh line add karo
#
#  ── Log channel save ke baad ──────────────────────────────────────────────
#  DB.set_log_channel(guild_id, "mod_log", channel_id)
#  notify_bot(guild_id, "settings")   ← yeh line add karo
#
#  ── Automod save ke baad ──────────────────────────────────────────────────
#  DB.save_automod(guild_id, ...)
#  notify_bot(guild_id, "automod")    ← yeh line add karo
#
#  ── Premium activate ke baad ──────────────────────────────────────────────
#  DB.activate_premium(guild_id, plan, activated_by)
#  notify_bot(guild_id, "premium")    ← yeh line add karo
#
#  ── Kuch bhi save karo aur sure nahi kya type hai ─────────────────────────
#  notify_bot(guild_id, "all")        ← sab reload kar dega (safe option)
#
# ══════════════════════════════════════════════════════════════════════════════
