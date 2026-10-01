#!/bin/bash
# Install finproj on a fresh Ubuntu 24.04 DigitalOcean droplet and serve it
# on port 8501. Run from the Mac, after the droplet exists:
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

cat > /etc/systemd/system/finproj.service << 'EOF'
[Unit]
Description=finproj Streamlit
After=network.target

[Service]
Type=simple
User=finproj
Group=finproj
WorkingDirectory=/home/finproj/finproj
ExecStart=/home/finproj/finproj/.venv/bin/python -m streamlit run gui/v1/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now finproj.service

ufw allow OpenSSH
ufw allow 8501/tcp
ufw --force enable

ip="$(hostname -I | awk '{print $1}')"
echo "finproj is starting. Open http://${ip}:8501"
