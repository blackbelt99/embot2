# ╔══════════════════════════════════════════════════════════════╗
# ║         Empire Prime — Web Dashboard                          ║
# ║  Manage your bot from browser — per-server settings         ║
# ╚══════════════════════════════════════════════════════════════╝

import os
import sys
import json
import secrets
import requests
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, jsonify, flash)
from dotenv import load_dotenv

# Load .env from parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add parent dir to path for db import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import db as DB
print(f"[DASHBOARD] Using DB: {DB.DB_PATH}")

# Auto-sync bridge — dashboard changes → bot memory (10s mein reflect)
try:
    from sync_api import notify_bot
except ImportError:
    def notify_bot(guild_id, change_type="all"):
        pass  # sync_api.py nahi mili — silently skip

app = Flask(__name__)
app.secret_key = os.getenv('DASHBOARD_SECRET', secrets.token_hex(32))

# Admin user IDs — set ADMIN_USER_IDS in .env (comma separated Discord user IDs)
_admin_raw  = os.getenv('ADMIN_USER_IDS', '')
ADMIN_IDS   = {uid.strip() for uid in _admin_raw.split(',') if uid.strip()}

def is_admin(user_id: str) -> bool:
    return str(user_id) in ADMIN_IDS

@app.context_processor
def inject_globals():
    user = session.get('user')
    admin = is_admin(str(user.get('id',''))) if user else False
    return {'is_admin': admin, 'invite': BOT_INVITE}

# ─── Discord OAuth2 Config ────────────────────────────────────────────────────
CLIENT_ID     = os.getenv('DISCORD_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')
BOT_TOKEN     = os.getenv('BOT_TOKEN', '')
_base_url     = os.getenv('DASHBOARD_URL', 'http://localhost:5000').rstrip('/')
REDIRECT_URI  = _base_url + '/callback'
BOT_INVITE    = f'https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&scope=bot+applications.commands'

DISCORD_API   = 'https://discord.com/api/v10'
OAUTH_URL     = (
    f'https://discord.com/oauth2/authorize'
    f'?client_id={CLIENT_ID}'
    f'&redirect_uri={requests.utils.quote(REDIRECT_URI, safe="")}'
    f'&response_type=code'
    f'&scope=identify+guilds'
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def discord_request(endpoint, token=None, method='GET', data=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    else:
        headers['Authorization'] = f'Bot {BOT_TOKEN}'
    url = f'{DISCORD_API}{endpoint}'
    try:
        if method == 'GET':
            r = requests.get(url, headers=headers, timeout=5)
        elif method == 'POST':
            r = requests.post(url, headers=headers, json=data, timeout=5)
        elif method == 'PATCH':
            r = requests.patch(url, headers=headers, json=data, timeout=5)
        return r.json() if r.content else {}
    except Exception:
        return {}

def get_bot_guilds():
    """Get all guilds the bot is in (with pagination to bypass 200 limit)."""
    guilds = {}
    after = None
    for _ in range(20):  # max 20 pages x 200 = 4000 guilds
        endpoint = '/users/@me/guilds?limit=200'
        if after:
            endpoint += f'&after={after}'
        data = discord_request(endpoint)
        if not isinstance(data, list) or not data:
            break
        for g in data:
            guilds[g['id']] = g
        if len(data) < 200:
            break
        after = data[-1]['id']
    return guilds

def get_guild_by_id(guild_id: str) -> dict:
    """Fetch a single guild by ID directly from Discord API (reliable for known guilds)."""
    data = discord_request(f'/guilds/{guild_id}')
    if isinstance(data, dict) and 'id' in data:
        return data
    return {}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_mutual_guilds():
    """Guilds where both user and bot are present."""
    user_token  = session.get('access_token')
    user_guilds = discord_request('/users/@me/guilds', token=user_token)
    bot_guilds  = get_bot_guilds()

    if not isinstance(user_guilds, list):
        return [], []

    mutual = []
    not_in = []
    for g in user_guilds:
        perms = int(g.get('permissions', 0))
        is_admin = (perms & 0x8) == 0x8
        if not is_admin:
            continue
        if g['id'] in bot_guilds:
            g['bot_in'] = True
            mutual.append(g)
        else:
            g['bot_in'] = False
            not_in.append(g)
    return mutual, not_in


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    user = session.get('user')
    return render_template('index.html', user=user, invite=BOT_INVITE)


@app.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(OAUTH_URL)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))

    # Exchange code for token
    data = {
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type':    'authorization_code',
        'code':          code,
        'redirect_uri':  REDIRECT_URI,
    }
    r = requests.post(f'{DISCORD_API}/oauth2/token', data=data,
                      headers={'Content-Type': 'application/x-www-form-urlencoded'})
    tokens = r.json()
    access_token = tokens.get('access_token')
    if not access_token:
        return redirect(url_for('index'))

    session['access_token'] = access_token

    # Get user info
    user = discord_request('/users/@me', token=access_token)
    session['user'] = user

    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    mutual, not_in = get_mutual_guilds()
    return render_template('dashboard.html',
                           user=session['user'],
                           mutual=mutual,
                           not_in=not_in,
                           invite=BOT_INVITE)


@app.route('/server/<guild_id>')
@login_required
def server(guild_id):
    # Verify user has admin in this guild
    mutual, _ = get_mutual_guilds()
    guild = next((g for g in mutual if g['id'] == guild_id), None)
    if not guild:
        flash('You do not have access to this server.', 'error')
        return redirect(url_for('dashboard'))

    gid = int(guild_id)

    # Load all settings from DB
    antinuke = DB.get_antinuke(gid)
    guild_cfg = DB.get_guild(gid)
    antispam  = DB.get_antispam(gid)
    automod   = DB.get_automod(gid)
    wl_users  = list(DB.wl_get_users(gid))
    wl_roles  = list(DB.wl_get_roles(gid))
    admins    = list(DB.admin_get(gid))
    verify    = DB.get_verify_config(gid)
    ticket    = DB.get_ticket_config(gid)

    # Load all welcome configs
    try:
        welcome_data = {
            'join':  DB.get_welcome(gid, 'join'),
            'leave': DB.get_welcome(gid, 'leave'),
            'boost': DB.get_welcome(gid, 'boost'),
        }
    except Exception:
        welcome_data = {'join': {}, 'leave': {}, 'boost': {}}
    welcome = welcome_data.get('join', {})  # backwards compat

    # Load premium feature configs
    import json as _json
    def _pget(key, default=None):
        try:
            val = DB.get_premium_config(gid, key)
            if val is None: return default
            return _json.loads(val) if isinstance(val, str) and val.startswith(('{','[')) else val
        except: return default

    premium_cfg = {
        'level_enabled':    _pget('level_config', {}).get('enabled', False) if isinstance(_pget('level_config', {}), dict) else False,
        'level_channel':    _pget('level_config', {}).get('channel', '') if isinstance(_pget('level_config', {}), dict) else '',
        'autorole':         _pget('autorole', []),
        'autoreact':        _pget('autoreact', {}),
        'wordreact':        _pget('wordreact', {}),
        'autoresponder':    _pget('autoresponder', {}),
        'tempvc':           _pget('tempvc', 0),
    }

    return render_template('server.html',
        user=session['user'],
        guild=guild,
        guild_id=guild_id,
        antinuke=antinuke,
        guild_cfg=guild_cfg,
        antispam=antispam,
        automod=automod,
        wl_users=wl_users,
        wl_roles=wl_roles,
        admins=admins,
        verify=verify,
        ticket=ticket,
        welcome=welcome,
        welcome_data=welcome_data,
        premium_cfg=premium_cfg,
    )


# ─── API Endpoints (called from JS) ──────────────────────────────────────────

@app.route('/api/<guild_id>/antinuke', methods=['POST'])
@login_required
def api_antinuke(guild_id):
    gid  = int(guild_id)
    data = request.json or {}
    kwargs = {}
    if 'enabled'    in data: kwargs['enabled']    = int(data['enabled'])
    if 'punishment' in data: kwargs['punishment'] = data['punishment']
    if 'raid_shield'in data: kwargs['raid_shield']= int(data['raid_shield'])
    if kwargs:
        DB.set_antinuke(gid, **kwargs)

    notify_bot(gid, "antinuke")  # Bot ko instantly batao

    # Notify in antinuke log channel that settings were updated from dashboard
    try:
        cfg = DB.get_antinuke(gid)
        log_ch = cfg.get('log_channel')
        if log_ch:
            status = "✅ ENABLED" if kwargs.get('enabled', cfg.get('enabled')) else "❌ DISABLED"
            discord_request(
                f'/channels/{log_ch}/messages',
                method='POST',
                data={'content': f'🛡️ **Anti-Nuke settings updated from Dashboard**\nStatus: **{status}** | Punishment: **{kwargs.get("punishment", cfg.get("punishment", "ban"))}**'}
            )
    except Exception:
        pass
    return jsonify({'ok': True})


@app.route('/api/<guild_id>/antispam', methods=['POST'])
@login_required
def api_antispam(guild_id):
    gid  = int(guild_id)
    data = request.json or {}
    DB.set_antispam(gid, bool(data.get('enabled', False)))
    notify_bot(gid, "antispam")  # Bot ko instantly batao
    return jsonify({'ok': True})


@app.route('/api/<guild_id>/prefix', methods=['POST'])
@login_required
def api_prefix(guild_id):
    gid    = int(guild_id)
    data   = request.json or {}
    prefix = data.get('prefix', '$')[:5]
    DB.set_prefix(gid, prefix)
    notify_bot(gid, "settings")  # Bot ko instantly batao
    return jsonify({'ok': True, 'prefix': prefix})


@app.route('/api/<guild_id>/logs', methods=['POST'])
@login_required
def api_logs(guild_id):
    gid  = int(guild_id)
    data = request.json or {}
    for lt in ('bot_log', 'mod_log', 'invite_log', 'ticket_log'):
        if lt in data:
            try:
                DB.set_log_channel(gid, lt, int(data[lt] or 0))
            except Exception:
                pass
    # Antinuke log channel
    if 'antinuke_log' in data:
        try:
            DB.set_antinuke(gid, log_channel=int(data['antinuke_log'] or 0))
        except Exception:
            pass
    notify_bot(gid, "settings")  # Bot ko instantly batao
    return jsonify({'ok': True})


@app.route('/api/<guild_id>/welcome', methods=['POST'])
@login_required
def api_welcome(guild_id):
    gid      = int(guild_id)
    data     = request.json or {}
    msg_type = data.get('msg_type', 'join')
    if msg_type not in ('join', 'leave', 'boost'):
        msg_type = 'join'
    try:
        kwargs = {}
        if 'enabled'     in data:
            try: kwargs['enabled']    = int(data['enabled'])
            except: pass
        if 'channel_id'  in data:
            try: kwargs['channel_id'] = int(data['channel_id'] or 0)
            except: kwargs['channel_id'] = 0
        if 'title'       in data: kwargs['title']       = data['title']
        if 'description' in data: kwargs['description'] = data['description']
        if 'color'       in data: kwargs['color']       = data['color']
        if 'thumbnail'   in data: kwargs['thumbnail']   = data['thumbnail']
        if 'image_url'   in data: kwargs['image_url']   = data['image_url']
        if 'footer_text' in data: kwargs['footer_text'] = data['footer_text']
        if 'show_fields' in data:
            try: kwargs['show_fields'] = int(data['show_fields'])
            except: pass
        DB.save_welcome(gid, msg_type=msg_type, **kwargs)
        notify_bot(gid, "settings")  # Bot ko instantly batao
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/api/<guild_id>/whitelist/add', methods=['POST'])
@login_required
def api_wl_add(guild_id):
    gid     = int(guild_id)
    data    = request.json or {}
    user_id = data.get('user_id')
    if user_id:
        DB.wl_add_user(gid, int(user_id))
    notify_bot(gid, "antinuke")  # Bot ko instantly batao
    return jsonify({'ok': True})


@app.route('/api/<guild_id>/whitelist/remove', methods=['POST'])
@login_required
def api_wl_remove(guild_id):
    gid     = int(guild_id)
    data    = request.json or {}
    user_id = data.get('user_id')
    if user_id:
        DB.wl_remove_user(gid, int(user_id))
    notify_bot(gid, "antinuke")  # Bot ko instantly batao
    return jsonify({'ok': True})


@app.route('/api/<guild_id>/automod', methods=['POST'])
@login_required
def api_automod(guild_id):
    gid  = int(guild_id)
    data = request.json or {}
    if 'settings' in data:
        DB.save_automod_settings(gid, data['settings'])
    if 'punishment' in data:
        DB.save_automod_punishment(gid, data['punishment'])
    notify_bot(gid, "automod")  # Bot ko instantly batao
    return jsonify({'ok': True})


@app.route('/api/stats')
def api_stats():
    """Public stats endpoint."""
    try:
        bot_info = discord_request('/users/@me')
        guilds   = discord_request('/users/@me/guilds')
        guild_count = len(guilds) if isinstance(guilds, list) else '?'
        return jsonify({
            'bot_name': bot_info.get('username', 'Empire Prime'),
            'guilds':   guild_count,
            'status':   'online'
        })
    except Exception:
        return jsonify({'status': 'offline'})



@app.route('/api/<guild_id>/ticket', methods=['POST'])
@login_required
def api_ticket(guild_id):
    gid  = int(guild_id)
    data = request.json or {}
    kwargs = {}
    if 'panel_title'   in data: kwargs['panel_title']   = data['panel_title']
    if 'panel_desc'    in data: kwargs['panel_desc']     = data['panel_desc']
    if 'panel_rules'   in data:
        rules = data['panel_rules']
        if isinstance(rules, list):
            kwargs['panel_rules'] = rules
        elif isinstance(rules, str):
            kwargs['panel_rules'] = [r.strip() for r in rules.split('\n') if r.strip()]
    if 'support_hours' in data: kwargs['support_hours']  = data['support_hours']
    if 'footer'        in data: kwargs['footer']         = data['footer']
    if 'close_dm'      in data: kwargs['close_dm']       = data['close_dm']
    if 'ping_role'     in data:
        try:
            kwargs['ping_role'] = int(data['ping_role'] or 0)
        except (ValueError, TypeError):
            kwargs['ping_role'] = 0
    if 'min_account_age' in data:
        try:
            kwargs['min_account_age'] = max(0, int(data['min_account_age'] or 0))
        except (ValueError, TypeError):
            kwargs['min_account_age'] = 0
    if 'max_tickets' in data:
        try:
            kwargs['max_tickets'] = max(1, int(data['max_tickets'] or 1))
        except (ValueError, TypeError):
            kwargs['max_tickets'] = 1
    if kwargs:
        DB.save_ticket_config(gid, **kwargs)

    notify_bot(gid, "settings")  # Bot ko instantly batao

    # Also trigger ticket panel refresh via Discord message if channel is set
    try:
        cfg = DB.get_ticket_config(gid)
        panel_ch = cfg.get('panel_channel_id') or cfg.get('channel_id')
        if panel_ch:
            discord_request(
                f'/channels/{panel_ch}/messages',
                method='POST',
                data={'content': '🔄 Ticket settings updated from dashboard. Run `$ticket panel` to refresh the panel.'}
            )
    except Exception:
        pass
    return jsonify({'ok': True})


@app.route('/api/<guild_id>/verify', methods=['POST'])
@login_required
def api_verify(guild_id):
    gid  = int(guild_id)
    data = request.json or {}
    kwargs = {}
    try:
        if 'verified_role'   in data: kwargs['verified_role']   = int(data['verified_role']   or 0)
        if 'unverified_role' in data: kwargs['unverified_role'] = int(data['unverified_role'] or 0)
        if 'verify_channel'  in data: kwargs['verify_channel']  = int(data['verify_channel']  or 0)
        if 'log_channel'     in data: kwargs['log_channel']     = int(data['log_channel']     or 0)
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'error': 'Invalid ID'})
    if kwargs:
        DB.save_verify_config(gid, **kwargs)
    notify_bot(gid, "verify")  # Bot ko instantly batao
    return jsonify({'ok': True})


# ─── Premium Feature APIs ────────────────────────────────────────────────────

@app.route('/api/<guild_id>/premium/level', methods=['POST'])
@login_required
def api_premium_level(guild_id):
    import json as _j
    gid  = int(guild_id)
    data = request.json or {}
    try:
        existing_raw = DB.get_premium_config(gid, 'level_config')
        existing = _j.loads(existing_raw) if existing_raw else {}
    except: existing = {}
    if 'enabled' in data: existing['enabled'] = bool(data['enabled'])
    if 'channel' in data: existing['channel'] = int(data['channel']) if data['channel'] else None
    DB.set_premium_config(gid, 'level_config', _j.dumps(existing))
    notify_bot(gid, 'all')
    return jsonify({'ok': True})

@app.route('/api/<guild_id>/premium/autorole', methods=['POST'])
@login_required
def api_premium_autorole(guild_id):
    import json as _j
    gid  = int(guild_id)
    data = request.json or {}
    action = data.get('action')
    try:
        existing_raw = DB.get_premium_config(gid, 'autorole')
        existing = _j.loads(existing_raw) if existing_raw else []
    except: existing = []
    if action == 'add' and data.get('role_id'):
        rid = int(data['role_id'])
        if rid not in existing: existing.append(rid)
    elif action == 'remove' and data.get('role_id'):
        rid = int(data['role_id'])
        existing = [r for r in existing if r != rid]
    DB.set_premium_config(gid, 'autorole', _j.dumps(existing))
    notify_bot(gid, 'all')
    return jsonify({'ok': True, 'roles': existing})

@app.route('/api/<guild_id>/premium/autoreact', methods=['POST'])
@login_required
def api_premium_autoreact(guild_id):
    import json as _j
    gid  = int(guild_id)
    data = request.json or {}
    action = data.get('action')
    try:
        existing_raw = DB.get_premium_config(gid, 'autoreact')
        existing = _j.loads(existing_raw) if existing_raw else {}
    except: existing = {}
    if action == 'set' and data.get('channel_id') and data.get('emojis'):
        existing[str(data['channel_id'])] = data['emojis'].split()
    elif action == 'remove' and data.get('channel_id'):
        existing.pop(str(data['channel_id']), None)
    DB.set_premium_config(gid, 'autoreact', _j.dumps(existing))
    notify_bot(gid, 'all')
    return jsonify({'ok': True, 'data': existing})

@app.route('/api/<guild_id>/premium/wordreact', methods=['POST'])
@login_required
def api_premium_wordreact(guild_id):
    import json as _j
    gid  = int(guild_id)
    data = request.json or {}
    action = data.get('action')
    try:
        existing_raw = DB.get_premium_config(gid, 'wordreact')
        existing = _j.loads(existing_raw) if existing_raw else {}
    except: existing = {}
    if action == 'add' and data.get('keyword') and data.get('emojis'):
        existing[data['keyword'].lower()] = data['emojis'].split()
    elif action == 'remove' and data.get('keyword'):
        existing.pop(data['keyword'].lower(), None)
    DB.set_premium_config(gid, 'wordreact', _j.dumps(existing))
    notify_bot(gid, 'all')
    return jsonify({'ok': True, 'data': existing})

@app.route('/api/<guild_id>/premium/autoresponder', methods=['POST'])
@login_required
def api_premium_autoresponder(guild_id):
    import json as _j
    gid  = int(guild_id)
    data = request.json or {}
    action = data.get('action')
    try:
        existing_raw = DB.get_premium_config(gid, 'autoresponder')
        existing = _j.loads(existing_raw) if existing_raw else {}
    except: existing = {}
    if action == 'add' and data.get('trigger') and data.get('response'):
        existing[data['trigger']] = data['response']
    elif action == 'remove' and data.get('trigger'):
        existing.pop(data['trigger'], None)
    DB.set_premium_config(gid, 'autoresponder', _j.dumps(existing))
    notify_bot(gid, 'all')
    return jsonify({'ok': True, 'data': existing})

@app.route('/api/<guild_id>/premium/tempvc', methods=['POST'])
@login_required
def api_premium_tempvc(guild_id):
    import json as _j
    gid  = int(guild_id)
    data = request.json or {}
    ch_id = int(data.get('channel_id') or 0)
    DB.set_premium_config(gid, 'tempvc', ch_id)
    notify_bot(gid, 'all')
    return jsonify({'ok': True})

# ─── Public Pricing ──────────────────────────────────────────────────────────

@app.route('/pricing')
def pricing_page():
    plans  = DB.get_plans(active_only=True)
    notice = DB.get_site_config('pricing_notice')
    upi    = DB.get_site_config('upi_id')
    paypal = DB.get_site_config('paypal')
    contact= DB.get_site_config('contact_discord')
    discord_invite = DB.get_site_config('discord_invite')
    return render_template('pricing.html',
        user=session.get('user'),
        plans=plans,
        notice=notice, upi=upi, paypal=paypal,
        contact=contact, discord_invite=discord_invite,
        invite=BOT_INVITE)


# ─── Admin Panel ──────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get('user')
        if not user or not is_admin(str(user.get('id',''))):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin')
@admin_required
def admin_panel():
    stats        = DB.get_stats()
    plans        = DB.get_plans(active_only=False)
    recent_orders= DB.get_orders(limit=10)
    all_orders   = DB.get_orders(limit=200)
    site         = {
        'discord_invite': DB.get_site_config('discord_invite'),
        'contact_discord':DB.get_site_config('contact_discord'),
        'upi_id':         DB.get_site_config('upi_id'),
        'paypal':         DB.get_site_config('paypal'),
        'pricing_notice': DB.get_site_config('pricing_notice'),
        'bot_description':DB.get_site_config('bot_description'),
    }
    # Guild configs summary
    conn = DB.get_conn()
    gs_rows = conn.execute("SELECT guild_id, prefix FROM guild_settings").fetchall()
    an_rows = conn.execute("SELECT guild_id, enabled FROM antinuke").fetchall()
    conn.close()
    an_map = {r['guild_id']: r['enabled'] for r in an_rows}
    guild_cfgs = {}
    for r in gs_rows:
        gid = r['guild_id']
        guild_cfgs[gid] = {'prefix': r['prefix'], 'an_enabled': an_map.get(gid, 0)}
    total_guilds = len(guild_cfgs)
    return render_template('admin.html',
        user=session['user'], stats=stats,
        plans=plans, recent_orders=recent_orders,
        all_orders=all_orders, site=site,
        guild_cfgs=guild_cfgs, total_guilds=total_guilds,
        invite=BOT_INVITE)


@app.route('/admin/api/plan/save', methods=['POST'])
@admin_required
def admin_plan_save():
    data = request.json or {}
    if not data.get('name') or not data.get('price'):
        return jsonify({'ok': False, 'error': 'Name and price required'})
    try:
        features = data.get('features', [])
        if isinstance(features, str):
            features = [f.strip() for f in features.split('\n') if f.strip()]
        data['features'] = features
        if data.get('id'):
            data['id'] = int(data['id'])
        DB.save_plan(data)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/admin/api/plan/delete', methods=['POST'])
@admin_required
def admin_plan_delete():
    data = request.json or {}
    try:
        DB.delete_plan(int(data['id']))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/admin/api/order/update', methods=['POST'])
@admin_required
def admin_order_update():
    data = request.json or {}
    try:
        DB.update_order_status(int(data['id']), data['status'])
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/admin/api/order/delete', methods=['POST'])
@admin_required
def admin_order_delete():
    data = request.json or {}
    try:
        DB.delete_order(int(data['id']))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@app.route('/admin/api/site/save', methods=['POST'])
@admin_required
def admin_site_save():
    data = request.json or {}
    for key, val in data.items():
        DB.set_site_config(key, val)
    return jsonify({'ok': True})


# ─── Premium Server Management ───────────────────────────────────────────────

@app.route('/admin/premium')
@admin_required
def admin_premium():
    """Premium server management page."""
    premium_servers = DB.get_all_premium_servers()
    # Enrich with guild name — use DB cache (saved by bot on startup) as primary source
    db_guild_names = DB.get_all_guild_names()
    bot_guilds = get_bot_guilds()
    # Merge: DB names take priority, API fills gaps
    all_guilds = {**bot_guilds, **db_guild_names}
    for srv in premium_servers:
        gid = str(srv['guild_id'])
        g = all_guilds.get(gid)
        if not g:
            # Last resort: direct Discord API call for this specific guild
            g = get_guild_by_id(gid)
        srv['guild_name'] = g.get('name', f"Unknown ({gid})") if g else f"Unknown ({gid})"
        srv['guild_icon'] = g.get('icon') if g else None
    # Build combined guild list for dropdown (DB + API)
    db_names = DB.get_all_guild_names()
    combined_guilds = {**bot_guilds, **db_names}
    return render_template(
        'admin_premium.html',
        premium_servers=premium_servers,
        bot_guilds=sorted(combined_guilds.values(), key=lambda g: g.get('name',''))
    )

def _sync_premium_file():
    """Write all active premium guild IDs to premium_guilds.txt so bot can read them."""
    import pathlib
    try:
        servers = DB.get_all_premium_servers()
        ids = [str(s['guild_id']) for s in servers]
        pf = pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent / "premium_guilds.txt"
        pf.write_text("\n".join(ids))
    except Exception as e:
        print(f"[WARN] Could not write premium_guilds.txt: {e}")

@app.route('/admin/api/premium/activate', methods=['POST'])
@admin_required
def admin_premium_activate():
    data = request.json or {}
    try:
        guild_id  = int(data['guild_id'])
        plan_name = data.get('plan_name', 'Premium')
        expires   = data.get('expires_at', '')
        admin     = session['user']['username']
        DB.activate_premium(guild_id, plan_name, admin, expires)
        _sync_premium_file()
        notify_bot(guild_id, "premium")  # Bot ko instantly batao
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/admin/api/premium/deactivate', methods=['POST'])
@admin_required
def admin_premium_deactivate():
    data = request.json or {}
    try:
        DB.deactivate_premium(int(data['guild_id']))
        _sync_premium_file()
        notify_bot(int(data['guild_id']), "premium")  # Bot ko instantly batao
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/admin/api/premium/status', methods=['GET'])
@admin_required
def admin_premium_status():
    guild_id = request.args.get('guild_id')
    if not guild_id:
        return jsonify({'ok': False, 'error': 'guild_id required'})
    data = DB.get_premium_server(int(guild_id))
    return jsonify({'ok': True, 'data': data})


# ─── Admin: Sync guild names from Discord API into DB ────────────────────────
@app.route('/admin/api/sync-guilds', methods=['POST'])
@admin_required
def admin_sync_guilds():
    """Fetch all bot guilds from Discord API and save names to DB."""
    try:
        bot_guilds = get_bot_guilds()
        count = 0
        for gid, g in bot_guilds.items():
            try:
                DB.save_guild_name(int(gid), g.get('name',''), g.get('icon','') or '')
                count += 1
            except: pass
        return jsonify({'ok': True, 'synced': count, 'total_api': len(bot_guilds)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5000))
    debug = os.getenv('DASHBOARD_DEBUG', 'false').lower() == 'true'
    print(f'[Dashboard] Starting on http://0.0.0.0:{port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
