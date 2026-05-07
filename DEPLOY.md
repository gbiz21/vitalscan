# Deploying VitalScan to your homelab

Target: `https://vitalscan.bkre8tive.com` via a named Cloudflare Tunnel.
No port forwarding, no public IP exposure, no Traefik in the path.

## Architecture

```
browser → vitalscan.bkre8tive.com → Cloudflare edge → Argo Tunnel
       → cloudflared (homelab) → vitalscan-frontend:80 → vitalscan-backend
```

Cloudflare terminates TLS at the edge — no Let's Encrypt needed on the
homelab. The tunnel is outbound-only, so the homelab firewall stays closed.

## Prerequisites

- A Docker host on your homelab (Synology, Proxmox VM, bare metal — any).
- Outbound internet from that host (the tunnel calls home; no inbound).
- The Cloudflare zone `bkre8tive.com` is already set up (active in CF, NS
  pointing at `meg.ns.cloudflare.com` / `tosana.ns.cloudflare.com`).
- The named tunnel `vitalscan` is already created in the CF account, and
  `vitalscan.bkre8tive.com` is already CNAMEd to its `cfargotunnel.com`
  origin. (Both done — see deploy/cloudflared/config.yml for the UUID.)

## Step 1 — Ship the project to the homelab

From your Mac:

```bash
cd /Users/gbeazer/05_Projects
rsync -avz --exclude-from=vitalscan/.gitignore vitalscan/ \
  <homelab-user>@<homelab-host>:/srv/docker/vitalscan/
```

The `.gitignore` excludes `deploy/cloudflared/*.json` so the tunnel
credentials are NOT shipped by rsync. Ship them separately in step 2.

## Step 2 — Ship the tunnel credentials (one-time)

The credentials JSON contains the tunnel's `TunnelSecret`. It must be
present on the homelab but never committed.

```bash
scp ~/.cloudflared/86a4bbcd-b804-43a4-ae07-4daaf718bfb7.json \
  <homelab-user>@<homelab-host>:/srv/docker/vitalscan/deploy/cloudflared/
```

If you ever rotate the tunnel (delete + recreate), re-run this with the
new UUID and update `deploy/cloudflared/config.yml` to match.

## Step 3 — Bring it up on the homelab

```bash
ssh <homelab-user>@<homelab-host>
cd /srv/docker/vitalscan
docker compose up -d --build
docker compose logs -f cloudflared
```

You'll see `Connection registered connIndex=0` lines once the tunnel is
up. Hit `https://vitalscan.bkre8tive.com` from any browser.

## Step 4 — Switch from mock to real pipeline

By default the backend returns mock biomarker data so the dashboard is
useful before any video data is staged on the host. To run the real
POS rPPG pipeline:

```bash
echo "VITALSCAN_USE_MOCK=false" >> .env
docker compose up -d
```

For the dashboard demo (user uploads a video → biomarkers come back),
no host-side dataset is needed — the pipeline runs on whatever video the
browser sends.

## Common gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused: vitalscan-frontend:80` in cloudflared logs | Frontend container not up yet, or not on `vitalscan-internal` | `docker compose ps`; confirm both `vitalscan-frontend` and `vitalscan-cloudflared` show `running` |
| Browser shows `Error 1033 Argo Tunnel error` | Tunnel not running or wrong UUID in config.yml | `docker compose logs cloudflared` — look for auth errors; re-check UUID matches the JSON filename |
| Browser shows generic Cloudflare 1xxx error | DNS CNAME removed | Re-run `cloudflared tunnel route dns vitalscan vitalscan.bkre8tive.com` from your Mac |
| Backend returns 500 on `/scan` after flipping `VITALSCAN_USE_MOCK=false` | Real pipeline missing mediapipe in container | Confirm the backend Dockerfile uses Python 3.12 and full requirements.txt |

## Cost recap

- Domain: $0 additional (you own bkre8tive.com)
- Hosting: $0 (homelab)
- TLS: $0 (Cloudflare edge — no Let's Encrypt needed)
- DNS: $0 (Cloudflare free)
- Tunnel: $0 (cloudflared free tier)

**Total ongoing: $0/month.**
