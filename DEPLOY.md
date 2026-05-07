# Deploying VitalScan to your homelab

Target: `https://vitalscan.bkre8tive.com` via your existing Traefik + Let's Encrypt setup.

## Prerequisites (one-time)

You need these things already working on your homelab:

1. **A Docker host** — your Synology Container Manager, a Proxmox VM/LXC running Docker, or a bare-metal Docker machine. Any of them works.
2. **Traefik already running** on that host with:
   - `web` (port 80) and `websecure` (port 443) entrypoints
   - A cert resolver named `letsencrypt` (or rename it in `docker-compose.yml`)
   - An external Docker network it watches — assumed to be `traefik` (rename if yours is `web` / `proxy`)
3. **Ports 80 + 443 reachable from the internet** — port forwards on your UniFi router, or via a Cloudflare Tunnel if you go that route
4. **Cloudflare DNS for bkre8tive.com** (or wherever its DNS lives)

If any of these aren't set up, do those first — VitalScan deployment is the easy part once Traefik is serving anything else on that homelab.

## Step 1 — Add the DNS record

In Cloudflare DNS for `bkre8tive.com`:

| Type | Name      | Content                | Proxy   | TTL  |
|------|-----------|------------------------|---------|------|
| A    | vitalscan | `<homelab public IP>`  | DNS only* | Auto |

\* If you use Cloudflare proxy (orange cloud), Let's Encrypt's TLS-ALPN challenge will fail. Either set this record to "DNS only" (gray cloud) and let Traefik solve TLS-ALPN, or switch your Traefik resolver to use the Cloudflare DNS-01 challenge (more reliable but needs a Cloudflare API token).

Wait 1-2 minutes, then verify:
```bash
dig +short vitalscan.bkre8tive.com
# should print your homelab public IP
```

## Step 2 — Ship the project to the homelab

From your Mac:

```bash
# Copy the repo over (excludes venvs, node_modules, data via .gitignore)
cd /Users/gbeazer/05_Projects
rsync -avz --exclude-from=vitalscan/.gitignore vitalscan/ \
  <homelab-user>@<homelab-host>:/srv/docker/vitalscan/
```

Replace `<homelab-user>@<homelab-host>` with e.g. `gbeazer@homelab.local` or your Synology hostname. `/srv/docker/vitalscan/` is a convention — use whatever directory your Synology/Proxmox host stores docker stacks in.

## Step 3 — Bring it up on the homelab

SSH in:

```bash
ssh <homelab-user>@<homelab-host>
cd /srv/docker/vitalscan

# One-time: make sure the shared Traefik network exists
docker network ls | grep traefik || docker network create traefik

# Build and start
docker compose up -d --build

# Watch the logs while certs provision (first run takes 30-60 seconds)
docker compose logs -f
```

When you see `Application startup complete.` for the backend and the frontend nginx is serving, hit `https://vitalscan.bkre8tive.com` from any browser.

## Step 4 — Switch from mock to real pipeline

By default the backend runs in mock mode so the dashboard works before any video data is on the homelab. To run the real rPPG pipeline:

```bash
# On the homelab, edit the env or pass it inline
echo "VITALSCAN_USE_MOCK=false" > .env
docker compose up -d
```

You'll also need SCAMPS or UBFC video data on the homelab if you want to run evaluations there — but for the dashboard demo (someone clicks "Upload video" and gets biomarkers back), the pipeline runs against whatever video the user uploads in the browser, so no host-side data needed.

## Common Traefik gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `404 page not found` from Traefik | Container not on the `traefik` network | `docker network ls`, confirm both `vitalscan-frontend` and your Traefik container are on the same external network |
| Cert never provisions, browser shows TRAEFIK DEFAULT CERT | Resolver name in label doesn't match Traefik static config | Check Traefik logs for the resolver name, update `traefik.http.routers.vitalscan.tls.certresolver` |
| Cert provisions but Cloudflare returns 521 | Cloudflare proxy on (orange cloud) blocking the origin | Set DNS record to "DNS only" (gray cloud) |
| Backend returns 500 on `/scan` | Real pipeline mode + no mediapipe in container | Container build needs the full `requirements.txt` — confirm Dockerfile is using Python 3.12 base image |

## Recommended host: Synology vs Proxmox

You have both. My read:

- **Synology Container Manager** is the path of least resistance. Drop the project in `/volume1/docker/vitalscan/`, point Container Manager at the docker-compose file, click run. Traefik probably already lives here.
- **Proxmox VM/LXC with Docker** is more flexible (snapshots, easier to nuke and rebuild) but has more moving parts. Pick this if you're already running other Docker stacks on a Proxmox VM.

Either way the docker-compose config is identical.

## What to tell the demo audience

> "VitalScan runs at https://vitalscan.bkre8tive.com. You can upload a 30-second face video or use the Scan live button to capture from your webcam. The backend runs the POS rPPG algorithm we implemented — the same code that produced the SCAMPS evaluation table in the writeup."

## Cost recap

- Domain: $0 additional (you already own bkre8tive.com)
- Hosting: $0 additional (using existing homelab)
- TLS cert: $0 (Let's Encrypt via Traefik)
- DNS: $0 (Cloudflare free tier)

**Total ongoing: $0/month.**
