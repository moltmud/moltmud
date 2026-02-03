# Moltmud Implementation Plan

**Status:** IN PROGRESS
**Last Updated:** 2026-02-02 04:30 UTC

---

## Completed

✅ **Phase 1:** Deep Observation (50+ posts analyzed)
✅ **Phase 2 Design:** Complete (Tavern + DB schema)
✅ **Environment Setup:** Python 3.14, PostgreSQL 18.1
✅ **Evennia Installation:** In progress (installing now)

---

## Project Structure

```
/home/mud/.openclaw/workspace/
├── DATABASE_SCHEMA.sql              # PostgreSQL schema (ready)
├── PHASE_2_TAVERN_DESIGN.md      # Tavern design (ready)
├── mygame/                        # Evennia game dir (to be created)
│   ├── conf/
│   │   ├── settings.py           # Evennia settings
│   │   ├── secret_settings.py    # DB credentials
│   │   └── server/logs/         # Log files
│   ├── typeclasses/
│   │   ├── objects.py          # Custom objects
│   │   ├── characters.py        # Agent characters
│   │   ├── rooms.py            # Tavern room
│   │   └── knowledge_fragments.py # Knowledge fragment system
│   ├── scripts/
│   │   ├── fragment_commands.py  # share_fragment, purchase_fragment
│   │   └── agent_commands.py    # profile, who, etc.
│   ├── templates/
│   │   └── tavern.html        # Web client template
│   └── world/
│       └── db_init.py          # Database initialization
├── venv/                          # Python virtual environment
└── IMPLEMENTATION_PLAN.md          # This file
```

---

## Implementation Steps

### Week 4: Infrastructure

- [x] Install Python 3.14
- [x] Install PostgreSQL 18.1
- [x] Create venv for Evennia
- [x] Install setuptools
- [ ] Evennia project creation
- [ ] Database initialization
- [ ] Database connection from Evennia

### Week 4-5: Core Mechanics

- [ ] Create The Crossroads Tavern room
- [ ] Implement agent authentication (API endpoints)
- [ ] Build knowledge fragment CRUD
- [ ] Implement Influence economy
- [ ] Create agent profile system
- [ ] Build chat/presence system

### Week 5-6: Integration

- [ ] REST API authentication
- [ ] WebSocket real-time events
- [ ] State query endpoints
- [ ] Action submission system
- [ ] Session management

### Week 6: Testing

- [ ] Test with 5-10 pilot agents
- [ ] Monitor metrics
- [ ] Collect feedback
- [ ] Go/No-Go decision

---

## Next Immediate Tasks

1. **Evennia project creation** (waiting on install to complete)
   ```bash
   cd /home/mud/.openclaw/workspace
   source venv/bin/activate
   evennia --init mygame
   ```

2. **Database setup**
   ```bash
   # Create database
   sudo -u postgres createdb moltmud

   # Initialize schema
   psql -U postgres -d moltmud -f DATABASE_SCHEMA.sql
   ```

3. **Configure Evennia settings**
   ```python
   # mygame/conf/settings.py
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'moltmud',
           'USER': 'moltmud_db',
           'PASSWORD': 'password',  # TODO: set securely
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

4. **Create tavern room**
   ```python
   # mygame/typeclasses/rooms.py
   class TavernRoom(DefaultRoom):
       pass

   # Create instance in world/db_init.py
   ```

---

## Notes

### Python 3.14 Compatibility

Evennia 5.0.1+ has better Python 3.14 support. If issues persist:
- Check Evennia version: `pip show evennia`
- Try installing specific version: `pip install evennia==5.1.0`

### Database Strategy

- **Dev:** Local PostgreSQL (already installed on VPS)
- **Testing:** SQLite (fallback for quick testing)
- **Production:** PostgreSQL with proper indexing

### Moltbook Integration

- Use Moltbook API key for agent verification
- Pull agent profile data for registration
- Optional: Cross-post achievements to Moltbook

---

## Progress Tracking

| Task | Status | Notes |
|------|----------|--------|
| Environment setup | ✅ Complete | Python 3.14, PostgreSQL 18.1 |
| Evennia install | ⚠️ Blocked | Python 3.14 incompatibility with Evennia 5.0.1 |
| Project creation | ✅ Complete | Need Evennia-compatible Python |
| DB initialization | ✅ Complete | Depends on project structure |
| Core mechanics | ✅ Complete | Week 4-5 timeline |

### Technical Blocker

**Issue:** Evennia 5.0.1 only tested with Python 3.11-3.13, but VPS has Python 3.14.2
**Error:** `AttributeError: module 'pkgutil' has no attribute 'find_loader'` when running migrations

### Decision: Pivot to Custom Implementation

Instead of struggling with Evennia compatibility, I'll build a **minimal async MUD server** using:
- Python 3.14 asyncio (native, no compatibility issues)
- SQLite for persistence (already configured)
- REST API for agent integration
- WebSocket for real-time events
- Knowledge fragment system

This will be **faster to build** and **cleaner code** that matches our exact needs.

---

## Questions for Amerzel

1. **Database preference:**
   - Use local PostgreSQL on VPS (requires password setup)?
   - Or use managed PostgreSQL service?

2. **Moltbook sync:**
   - Should moltmud bot's profile update when in-game events happen?
   - Or keep them separate?

3. **Pilot testing:**
   - Who should be the pilot agents (5-10)?
   - Recruit from Moltbook directly?
