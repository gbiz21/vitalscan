#!/usr/bin/env bash
# Add (or update) a Unbound host override in OPNsense via REST API.
#
# Usage:
#   export OPNSENSE_URL=https://10.10.10.1     # or https://opnsense.lab... etc
#   export OPNSENSE_KEY=<your_api_key>
#   export OPNSENSE_SECRET=<your_api_secret>
#   ./deploy/opnsense-add-host.sh vitalscan lab.bkre8tive.com 10.10.10.6
#
# To generate API credentials in OPNsense:
#   System -> Access -> Users -> click your user -> scroll to "API keys"
#   -> click + -> a .txt downloads with key=... and secret=...
#
# This script also calls reconfigure() so the change applies immediately —
# no need to click the orange Apply banner in the UI.

set -euo pipefail

HOST="${1:?host required (e.g. vitalscan)}"
DOMAIN="${2:?domain required (e.g. lab.bkre8tive.com)}"
IP="${3:?ip required (e.g. 10.10.10.6)}"
DESCRIPTION="${4:-managed by deploy script}"

: "${OPNSENSE_URL:?OPNSENSE_URL not set}"
: "${OPNSENSE_KEY:?OPNSENSE_KEY not set}"
: "${OPNSENSE_SECRET:?OPNSENSE_SECRET not set}"

CURL=(curl -sk -u "${OPNSENSE_KEY}:${OPNSENSE_SECRET}")

echo "Checking if ${HOST}.${DOMAIN} already exists..."
existing=$("${CURL[@]}" "${OPNSENSE_URL}/api/unbound/settings/searchHostOverride" \
  -H "Content-Type: application/json" \
  -d "{\"searchPhrase\":\"${HOST}.${DOMAIN}\"}" \
  | python3 -c "import json, sys; rows = json.load(sys.stdin).get('rows', []); m=[r for r in rows if r.get('hostname')==\"${HOST}\" and r.get('domain')==\"${DOMAIN}\"]; print(m[0]['uuid'] if m else '')" )

if [ -n "${existing}" ]; then
  echo "Updating existing override (uuid=${existing})..."
  "${CURL[@]}" "${OPNSENSE_URL}/api/unbound/settings/setHostOverride/${existing}" \
    -H "Content-Type: application/json" \
    -d "{\"host\":{\"enabled\":\"1\",\"hostname\":\"${HOST}\",\"domain\":\"${DOMAIN}\",\"rr\":\"A\",\"server\":\"${IP}\",\"description\":\"${DESCRIPTION}\"}}" \
    | python3 -m json.tool
else
  echo "Adding new override..."
  "${CURL[@]}" "${OPNSENSE_URL}/api/unbound/settings/addHostOverride" \
    -H "Content-Type: application/json" \
    -d "{\"host\":{\"enabled\":\"1\",\"hostname\":\"${HOST}\",\"domain\":\"${DOMAIN}\",\"rr\":\"A\",\"server\":\"${IP}\",\"description\":\"${DESCRIPTION}\"}}" \
    | python3 -m json.tool
fi

echo "Applying configuration (Unbound reconfigure)..."
"${CURL[@]}" "${OPNSENSE_URL}/api/unbound/service/reconfigure" -X POST | python3 -m json.tool

echo ""
echo "Done. Verify with:"
echo "  dig +short ${HOST}.${DOMAIN}"
