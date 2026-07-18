# Scrabble VPS Operations Runbook

This is a local-only reference for operating and debugging the production Scrabble server. It is intentionally excluded from Git. Do not put passwords, private keys, session secrets, or the contents of `/etc/scrabble.env` here.

## Production layout

```text
Browser -> DNS/Cloudflare -> UFW -> Caddy -> Scrabble service -> SQLite
```

- Game: `https://play.debarro.dev`
- SSH alias/user/port: `vps`, `ubuntu`, `49153`
- Application checkout: `/opt/scrabble/app`
- Built frontend: `/srv/scrabble/frontend`
- Caddy configuration: `/etc/caddy/Caddyfile`
- Scrabble environment: `/etc/scrabble.env`
- Services: `caddy` and `scrabble`
- Backend listener: `127.0.0.1:5001`

Record these once finalized:

```text
Production database: TODO
Off-server backup destination: TODO
```

## Routine checks

```bash
ssh vps
systemctl status caddy
systemctl status scrabble
systemctl is-active caddy scrabble
curl -I https://play.debarro.dev
curl https://play.debarro.dev/api/health
sudo ss -tlnp
```

The health endpoint should return `{"status":"ok"}`. The public listeners should be ports 80, 443, and 49153. The backend must appear as `127.0.0.1:5001`, not `0.0.0.0:5001`.

## Logs

```bash
# Follow logs live
sudo journalctl -u scrabble -f
sudo journalctl -u caddy -f

# Recent logs
sudo journalctl -u scrabble -n 100 --no-pager
sudo journalctl -u caddy -n 100 --no-pager
sudo journalctl -u scrabble --since "30 minutes ago"
sudo journalctl -p err -b
```

Requests for `.env`, WordPress, GraphQL, and unrelated paths are normal automated scans. A 404 is appropriate. Investigate repeated 500 responses, crashes, authentication failures, or unusually heavy traffic.

## Restarting services

After changing the backend or `/etc/scrabble.env`:

```bash
sudo systemctl restart scrabble
sudo systemctl status scrabble
curl http://127.0.0.1:5001/api/health
```

After changing `/etc/caddy/Caddyfile`:

```bash
sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

If Scrabble fails to start:

```bash
sudo systemctl reset-failed scrabble
sudo systemctl restart scrabble
sudo journalctl -u scrabble -n 100 --no-pager
```

Use `reload` for Caddy when possible so existing connections are not unnecessarily interrupted.

## Diagnosing failures

Test from the outside inward.

### DNS

```bash
# On the VPS
getent ahosts play.debarro.dev

# On the local computer
dig +short play.debarro.dev
```

The result should include the VPS address.

### Public HTTPS and TLS

```bash
curl -v https://play.debarro.dev
```

This shows DNS resolution, connection establishment, TLS negotiation, and the HTTP response.

### Backend without Caddy

Run on the VPS:

```bash
curl http://127.0.0.1:5001/api/health
```

- Local health works but the public URL fails: inspect Caddy, TLS, DNS, Cloudflare, and UFW.
- Local health fails: inspect `scrabble` and its logs.
- Frontend works but `/api/health` fails: inspect Caddy's `/api/*` proxy route.
- Requests work but game updates fail: inspect browser console errors, `/ws/*`, and WebSocket logs.

### Caddy and firewall

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo journalctl -u caddy -n 100 --no-pager
sudo ufw status verbose
```

UFW should normally expose only:

```text
80/tcp
443/tcp
49153/tcp
```

Keep an existing SSH session open while changing SSH or firewall settings. Confirm a second connection works before closing it.

## Machine health

```bash
df -h
sudo du -xhd1 /var /opt /srv 2>/dev/null
free -h
top
ps aux --sort=-%mem | head
sudo journalctl -k -n 100 --no-pager
```

A full disk can stop SQLite writes, logging, deployments, and certificate renewal. Alert before usage reaches approximately 80-85%.

## SQLite and backups

Keep the production database in a persistent data directory outside the replaceable Git checkout. Use SQLite's online backup operation rather than copying an active database. Replace the example paths with explicit real paths:

```bash
sqlite3 /actual/path/scrabble.db ".backup '/actual/backup/path/scrabble-$(date +%F).db'"
```

Recommended policy:

- Run daily automated backups.
- Retain several days or weeks.
- Copy backups to another machine or provider.
- Test restoration periodically.
- Take a provider snapshot before major upgrades.

A backup on the same VPS is insufficient against disk or VPS loss. Never put the database or backups in `/srv/scrabble/frontend`, where Caddy could publish them.

## Security and updates

```bash
sudo apt update
apt list --upgradable
sudo apt upgrade

sudo systemctl status ssh
sudo sshd -t
sudo ufw status verbose
last
sudo journalctl -u ssh --since today
```

Take a database backup and provider snapshot before a major operating-system upgrade. Prefer SSH keys, keep private keys on trusted computers, and do not give the `scrabble` service account broad sudo access. If Cloudflare proxies the domain, use Full (strict) SSL mode.

## Deployment practice

```text
Edit locally -> test -> commit -> push -> deploy -> health check
```

A deployment should:

1. Check out the intended Git revision.
2. Install pinned backend dependencies.
3. Build the frontend.
4. Copy the frontend build to `/srv/scrabble/frontend`.
5. Run database migrations when migrations exist.
6. Restart `scrabble`.
7. Reload Caddy only if its configuration changed.
8. Check `/api/health` and the public frontend.
9. Roll back if a check fails.

Avoid editing production source directly or deploying from an uncommitted tree. Commit and push the change that makes the backend honor `SCRABBLE_HOST`; otherwise a future checkout can overwrite the production fix.

## Incident checklist

1. Confirm the failure from another browser or network.
2. Run the public curl checks.
3. Check `systemctl is-active caddy scrabble`.
4. Read the Scrabble and Caddy journals.
5. Test `127.0.0.1:5001/api/health` on the VPS.
6. Check disk, memory, listeners, and UFW.
7. Identify the most recent deployment or configuration change.
8. Roll back that change when appropriate.
9. Restore SQLite only after establishing database corruption or data loss.
10. After recovery, document the cause and prevention.

Do not delete logs, rebuild the VPS, or restore the database until the cause has been investigated and current data has been backed up.
