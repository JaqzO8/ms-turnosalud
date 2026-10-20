#!/usr/bin/env bash
set -euo pipefail
sha="${1:?Expected tested commit SHA}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]]
cd /opt/turno-salud/repo
exec 9>/opt/turno-salud/deploy.lock
flock -n 9
git fetch origin main
# An older queued run must never overwrite a newer main deployment.
if [[ "$(git rev-parse origin/main)" != "$sha" ]]; then
  echo "Superseded commit; skipping $sha"
  exit 0
fi
release="/opt/turno-salud/releases/$sha"
mkdir -p "$release"
git archive "$sha" | tar -x -C "$release"
cd "$release"
bash deploy/check-release.sh
python3.13 -m venv ms-citas/.venv
ms-citas/.venv/bin/pip install -r ms-citas/requirements.lock
python3.13 -m venv harness/.venv
harness/.venv/bin/pip install -r harness/requirements.lock
(cd ms-agenda && npm ci && npm run build)
# These files must use shell-compatible KEY=value entries, readable by the deploy user.
(set -a; source /etc/turno-salud/citas.env; set +a; cd ms-citas; .venv/bin/python -m app.db)
(set -a; source /etc/turno-salud/agenda.env; set +a; cd ms-agenda; bash scripts/migrate.sh)
previous="$(readlink -f /opt/turno-salud/current || true)"
activate() {
  ln -sfn "$1" /opt/turno-salud/current.next
  mv -Tf /opt/turno-salud/current.next /opt/turno-salud/current
  sudo systemctl restart agenda.service citas.service harness.service
}
rollback() {
  if [[ -n "$previous" && "$previous" != "$release" ]]; then
    activate "$previous" || true
    echo "Previous code restored. Database migrations are NOT automatically reversed." >&2
  fi
}
trap rollback ERR
activate "$release"
for port in 3001 3002 3003; do
  curl --fail --silent --show-error --retry 15 --retry-delay 2 --retry-connrefused \
    --max-time 5 "http://127.0.0.1:$port/health"
done
trap - ERR
echo "Deployment healthy: $sha"
