#!/usr/bin/env bash
# Run as root once on the fresh Amazon Linux 2023 demo instance.
set -euo pipefail
dnf install -y python3.13 python3.13-pip nodejs22 nodejs22-npm postgresql16-server nginx git
id turnosalud >/dev/null 2>&1 || useradd --create-home turnosalud
install -d -o turnosalud -g turnosalud /opt/turno-salud/releases /var/log/turno-salud
install -d -m 750 -o root -g turnosalud /etc/turno-salud
if [[ ! -f /var/lib/pgsql/data/PG_VERSION ]]; then
  postgresql-setup --initdb
fi
systemctl enable --now postgresql
if [[ ! -f /etc/turno-salud/citas.env ]]; then
  citas_password=$(openssl rand -hex 24)
  agenda_password=$(openssl rand -hex 24)
  runuser -u postgres -- psql -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE citas_user LOGIN PASSWORD '$citas_password';
CREATE ROLE agenda_user LOGIN PASSWORD '$agenda_password';
CREATE DATABASE citas_db OWNER citas_user;
CREATE DATABASE agenda_db OWNER agenda_user;
SQL
  printf "DATABASE_URL=postgresql+psycopg://citas_user:%s@127.0.0.1:5432/citas_db\nAGENDA_URL=http://127.0.0.1:3001\n" "$citas_password" > /etc/turno-salud/citas.env
  printf "DATABASE_URL=postgresql://agenda_user:%s@127.0.0.1:5432/agenda_db\nPORT=3001\nHOST=127.0.0.1\n" "$agenda_password" > /etc/turno-salud/agenda.env
  cat > /etc/turno-salud/harness.env <<'ENV'
MOCK_LLM=true
MS_AGENDA_URL=http://127.0.0.1:3001
MS_CITAS_URL=http://127.0.0.1:3002
LOGS_DIR=/var/log/turno-salud
ENV
  chown root:turnosalud /etc/turno-salud/*.env
  chmod 640 /etc/turno-salud/*.env
fi
# Password authentication over loopback; PostgreSQL remains private.
sed -i -E '/^host[[:space:]]/s/[[:space:]]ident$/ scram-sha-256/' /var/lib/pgsql/data/pg_hba.conf
systemctl reload postgresql
cat > /etc/nginx/default.d/turnosalud.conf <<'NGINX'
location / {
    proxy_pass http://127.0.0.1:3003;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 60s;
    client_max_body_size 16k;
}
NGINX
cat > /etc/nginx/conf.d/turnosalud-rate.conf <<'RATE'
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
RATE
cat >> /etc/nginx/default.d/turnosalud.conf <<'AUTH'
location ~ ^/portal/(login|register)$ {
    limit_req zone=auth_limit burst=5 nodelay;
    limit_req_status 429;
    proxy_pass http://127.0.0.1:3003;
    proxy_set_header Host $host;
    client_max_body_size 16k;
}
AUTH
nginx -t
systemctl enable --now nginx
systemctl reload nginx
