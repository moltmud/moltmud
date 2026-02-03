# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

### Browser (Windows Node)

- Browser runs on the Windows PC node via CDP (Chrome DevTools Protocol) on port 18800
- The browser profile name is **"openclaw"** — you MUST pass `"profile": "openclaw"` in the body of ALL browser.proxy requests
- Without the profile parameter, the node checks the default profile which has no browser, and returns `running: false, tabs: []`
- Example tab listing: `browser.proxy` with `{"path": "/tabs", "method": "GET", "body": {"profile": "openclaw"}}`
- Example start browser: `browser.proxy` with `{"path": "/start", "method": "POST", "body": {"profile": "openclaw"}}`
- Example open tab: `browser.proxy` with `{"path": "/tabs/open", "method": "POST", "body": {"profile": "openclaw", "url": "https://x.com"}}`
- The gateway does NOT have a local browser — all browser access goes through the Windows PC node
