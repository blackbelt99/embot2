# ⭐ Empire Prime Bot — Setup Guide

## Kya Add Kiya Gaya Hai

### Naye Files:
| File | Kya Hai |
|------|---------|
| `premium_bot.py` | Premium bot ka full code — sab advanced features |
| `dashboard/templates/admin_premium.html` | Admin panel mein Premium Servers tab |
| `.env.example` | Updated env template (PREMIUM_BOT_TOKEN add karo) |

### Purane Files Mein Changes:
| File | Kya Badla |
|------|-----------|
| `db.py` | Premium tables + functions add hue (bottom mein) |
| `dashboard/app.py` | Premium activate/deactivate API routes add hue |
| `dashboard/templates/admin.html` | "⭐ Premium Servers" nav link add hua |

---

## Premium Features List

### ☢️ Nuke Recovery (Crown Jewel)
- Server nuke detect karta hai (mass channel/role delete)
- **Sabhi banned members ko auto-unban** karta hai
- Har unbanned member ko **DM invite** bhejta hai
- Backup se **roles & channels restore** karta hai
- Full nuke report send karta hai
- Commands: `p!nukerecovery on/off`, `p!backup create/info`

### 💾 Server Backup
- Poore server ka snapshot save karta hai (roles, channels, emojis)
- Nuke recovery ke saath kaam karta hai
- `p!backup create` — backup banao
- `p!backup info` — backup details dekho

### 🎁 Giveaway System
- Duration-based giveaways (10m, 1h, 2d)
- Multiple winners support
- Auto-ends aur winner announce
- `p!gstart 1h 2 Nitro Classic`
- `p!gend <msg_id>`, `p!greroll <msg_id>`

### 🏆 Level / XP System
- Har message pe XP milta hai (60 sec cooldown)
- Level up announcements
- Level reward roles (specific level pe role auto-assign)
- Leaderboard with medals
- `p!rank`, `p!leaderboard`, `p!setlevel on/off/channel/addrole`

### 🎭 Reaction Roles
- Message pe reaction add karo → role milta hai
- Reaction remove → role wapas jaata hai
- Multiple emojis per message support
- `p!rr add <msg_id> <emoji> @role`

### 🤖 Auto Role
- Naya member join kare → automatically roles milte hain
- Multiple roles support
- `p!autorole add/remove/list @role`

### 📊 Polls
- Multi-option polls with number emojis
- Duration support
- `p!poll 1h Question | Option1 | Option2 | Option3`

### 🔊 Temp VC
- Hub VC join karo → apna personal VC milta hai
- Empty hone pe auto-delete
- `p!tempvc set #hub-channel`

### 📌 Sticky Messages
- Channel mein sticky message — hamesha sabse neeche rehta hai
- `p!sticky set <text>`, `p!sticky remove`

### 🔔 Reminders
- Personal reminders set karo
- `p!remind 30m Submit the assignment`

### 💬 Auto Responder
- Koi specific word likhe → bot auto-reply kare
- `p!ar add hi Hello there! | p!ar list`

### 🌟 Premium Welcome
- Custom embed welcome messages
- Placeholders: `{user}`, `{server}`, `{count}`, `{name}`
- Welcome DM support
- Custom embed color
- `p!setwelcome channel/message/dm/color/test`

### 🔍 Snipe
- Last deleted message dekho
- Last edited message dekho
- `p!snipe`, `p!editsnipe`

---

## Setup Steps

### Step 1: Discord Developer Portal
1. [discord.com/developers](https://discord.com/developers/applications) pe jao
2. **New Application** banao → name: "Empire Prime"
3. **Bot** section → "Add Bot" karo
4. Token copy karo

### Step 2: .env Update Karo
```env
PREMIUM_BOT_TOKEN=your_new_premium_bot_token_here
PREMIUM_BOT_NAME=Empire Prime
```

### Step 3: Premium Bot Run Karo
```bash
# Public bot (pehle se chal raha hai)
python bot.py

# Premium bot (alag terminal mein)
python premium_bot.py

# Dashboard
python dashboard/app.py
```

### Step 4: Premium Activate Karna (Dashboard se)
1. Dashboard open karo → **Admin Panel**
2. Left side mein **"⭐ Premium Servers"** click karo
3. Server select karo (jo buy kare)
4. Plan choose karo (Basic/Pro/Premium/VIP)
5. **Activate** button dabao
6. Ho gaya! Us server mein ab sab premium commands work karenge

### Step 5: User Ko Batao
Server mein type karo:
```
p!premiumhelp
```
Sab premium commands list ho jayenge.

---

## Default Prefix
Premium bot ka prefix hai: `p!`
(Change hoga agar server ne `$setprefix` use kiya ho — same DB use karta hai)

---

## Notes
- Premium bot aur public bot **alag-alag run hote hain** (alag tokens chahiye)
- Dono **same `db.py` aur `empire.db`** share karte hain — data sync rehta hai
- Premium features sirf `is_premium_server()` check ke baad activate hote hain
- Admin panel se **ek click mein** premium on/off kar sakte ho
