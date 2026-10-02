#!/bin/bash
# Install finproj on a fresh Ubuntu 24.04 DigitalOcean droplet and serve it
# over HTTPS on the public IP. Run from the Mac, after the droplet exists:
#   ssh root@THE_IP 'bash -s -- --on-droplet' < deploy/public-test.sh
set -euo pipefail

if [[ "${1:-}" != "--on-droplet" ]]; then
  echo "This script is for the droplet. From the finproj folder on the Mac, run:" >&2
  echo "  ssh root@THE_IP 'bash -s -- --on-droplet' < deploy/public-test.sh" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run it as root on the droplet." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git build-essential pkg-config python3 python3-venv python3-pip curl ca-certificates ufw

if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if ! id finproj >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" finproj
fi

sudo -u finproj bash -lc 'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y'

repo=/home/finproj/finproj
if [[ ! -d "$repo/.git" ]]; then
  sudo -u finproj git clone https://github.com/ajmscherer/finproj.git "$repo"
else
  sudo -u finproj git -C "$repo" pull --ff-only
fi

sudo -u finproj bash -lc "cd '$repo' && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt"
sudo -u finproj bash -lc "source \"\$HOME/.cargo/env\" && cd '$repo' && CARGO_BUILD_JOBS=1 cargo build --release --manifest-path rust/Cargo.toml -p finproj_engine"

# Account data stays outside the git checkout. The host secret is written
# only when it is already in the environment and billing.env does not exist.
install -d -o finproj -g finproj -m 700 /home/finproj/finproj-data
billing_env=/home/finproj/finproj-data/billing.env
if [[ -n "${FINPROJ_HOST_SECRET:-}" && ! -f "$billing_env" ]]; then
  (umask 077; printf 'FINPROJ_HOST_SECRET=%s\n' "$FINPROJ_HOST_SECRET" > "$billing_env")
  chown finproj:finproj "$billing_env"
  chmod 600 "$billing_env"
fi

cat > /etc/systemd/system/finproj.service << 'EOF'
[Unit]
Description=finproj Streamlit
After=network.target

[Service]
Type=simple
User=finproj
Group=finproj
WorkingDirectory=/home/finproj/finproj
Environment=FINPROJ_DATA_DIR=/home/finproj/finproj-data
EnvironmentFile=-/home/finproj/finproj-data/billing.env
ExecStart=/home/finproj/finproj/.venv/bin/python -m streamlit run gui/v1/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable finproj.service
systemctl restart finproj.service

apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
if [[ ! -f /usr/share/keyrings/caddy-stable-archive-keyring.gpg ]]; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  chmod o+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg
fi
if [[ ! -f /etc/apt/sources.list.d/caddy-stable.list ]]; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
  chmod o+r /etc/apt/sources.list.d/caddy-stable.list
  apt-get update
fi
apt-get install -y caddy

public_ip="$(curl -fsS --max-time 5 http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address || true)"
if [[ -z "$public_ip" ]]; then
  public_ip="$(curl -4 -fsS --max-time 5 https://api.ipify.org || true)"
fi
if [[ -z "$public_ip" ]]; then
  echo "Could not find the public IP, so HTTPS was not configured." >&2
  exit 1
fi

cat > /etc/caddy/Caddyfile << EOF
{
	default_sni ${public_ip}
}

${public_ip} {
	tls {
		issuer acme {
			profile shortlived
		}
	}
	reverse_proxy 127.0.0.1:8501 {
		flush_interval -1
	}
}
EOF

caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
systemctl enable caddy
systemctl restart caddy

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
ufw delete allow 8501/tcp || true

echo "finproj is starting. Open https://${public_ip}"
