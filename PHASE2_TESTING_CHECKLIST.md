# Lucky Bot Phase 2 Testing Checklist

Use this after deployment to verify moderation commands in a test server.

## 0) Setup
1. Invite bot with moderation permissions.
2. In test server, create users/roles for:
   - Server Owner
   - Moderator with `warn.exe` / `mute.exe` / `kick.exe` / `ban.exe`
   - Normal member
3. (Optional) Run your setup command if available to create `#mod-logs`.

## 1) Warning System
- `!warn @user ?r test warn`
- `/warn member:@user reason:test warn`
- `!warnings @user`
- `/warnings member:@user`
- `!unwarn @user` (remove latest)
- `!unwarn @user 1` (remove by number)
- `/unwarn member:@user number:1`
- `!clearwarn @user`
- `/clearwarn member:@user`

Expected:
- All responses are embeds.
- At 3+ warnings threshold message appears.
- Invalid warning number returns error embed.

## 2) Mute / Unmute
- `!mute @user ?t 10m ?r testing mute`
- `/mute member:@user duration:10m reason:testing mute`
- Invalid time checks:
  - `!mute @user ?t abc`
  - `/mute member:@user duration:abc`
- Long time checks (too long):
  - `!mute @user ?t 29d`
  - `/mute member:@user duration:29d`
- `!unmute @user`
- `/unmute member:@user`

Expected:
- Timeout is applied and removed correctly.
- Not-muted target returns informative embed.

## 3) Kick / Ban / Tempban
- `!kick @user ?r testing kick`
- `/kick member:@user reason:testing kick`
- `!ban @user ?r testing ban`
- `/ban member:@user reason:testing ban`
- `!tempban @user 10m ?r temp test`
- `/tempban member:@user duration:10m reason:temp test`

Expected:
- Protected targets (owner/extraowner/god bypass) are blocked.
- Tempban auto-unbans after duration expires.

## 4) Unban
- Ban at least two users with similar names then run:
  - `/unban username:partialname`

Expected:
- If multiple matches: bot should ask for more specific query (no accidental unban).
- If single match: unban succeeds and logs.

## 5) Permission Checks
Test commands from insufficient role account:
- `!warn`, `!mute`, `!kick`, `!ban`, `!tempban`

Expected:
- Permission error embeds show required role.

## 6) Log Validation
For each moderation action above, check `#mod-logs` for corresponding embed entries.

## 7) Slash/Prefix Parity
For every tested prefix command, test slash equivalent and confirm output + behavior matches.
