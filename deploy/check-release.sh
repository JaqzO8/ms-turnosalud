#!/usr/bin/env bash
set -euo pipefail
# Contract to agree with the agenda/harness owner before merging into main.
required=(ms-citas/requirements.lock ms-agenda/package.json ms-agenda/package-lock.json
  ms-agenda/scripts/migrate.sh harness/requirements.lock harness/app/main.py
  harness/tests deploy/systemd/agenda.service deploy/systemd/citas.service deploy/systemd/harness.service)
missing=0
for path in "${required[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing release component: $path" >&2
    missing=1
  fi
done
exit "$missing"
