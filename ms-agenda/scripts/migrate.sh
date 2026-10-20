#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DATABASE_URL="${DATABASE_URL:?DATABASE_URL requerida}"
node node_modules/tsx/dist/cli.mjs src/migrate.ts
