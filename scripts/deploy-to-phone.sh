#!/bin/bash
# PriusPilot — Deploy backend changes to Pocophone via SSH
# Usage: ./scripts/deploy-to-phone.sh [phone-host]
#
# Deploys modified Python/capnp files from the local repo to the phone's
# proot flowpilot installation. Requires SSH access to Termux (see DEPLOY.md).

set -euo pipefail

PHONE_HOST="${1:-pocophone}"
# Full path to proot flowpilot (Termux $PREFIX expanded)
PROOT_FP='/data/data/com.termux/files/usr/var/lib/proot-distro/installed-rootfs/ubuntu-jammy-fd/root/flowpilot'

echo "==> Deploying to $PHONE_HOST ..."

# Files to deploy (source path relative to repo root)
FILES=(
    # Core fixes
    "selfdrive/thermald/thermald.py"
    "cereal/log.capnp"
    "selfdrive/manager/flowinitd.py"
    "selfdrive/manager/process_config.py"
    "selfdrive/sentry.py"
    "launch_flowpilot.sh"

    # Prius Gen 2 car module
    "selfdrive/car/toyota_gen2/__init__.py"
    "selfdrive/car/toyota_gen2/values.py"
    "selfdrive/car/toyota_gen2/carstate.py"
    "selfdrive/car/toyota_gen2/carcontroller.py"
    "selfdrive/car/toyota_gen2/interface.py"
    "selfdrive/car/toyota_gen2/radar_interface.py"

    # DBC file for Prius Gen 2
    "opendbc/prius_gen2_pt.dbc"
)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

for f in "${FILES[@]}"; do
    SRC="$REPO_ROOT/$f"
    if [ ! -f "$SRC" ]; then
        echo "  SKIP $f (not found locally)"
        continue
    fi
    # Expand $PREFIX on the remote side
    DST_DIR=$(dirname "$f")
    ssh "$PHONE_HOST" "mkdir -p $PROOT_FP/$DST_DIR" 2>/dev/null
    scp -q "$SRC" "$PHONE_HOST:$PROOT_FP/$f"
    echo "  OK   $f"
done

echo "==> Deploy complete. Restart flowpilot on the phone to apply."
echo "    ssh $PHONE_HOST 'pkill -f launch_flowpilot'  # then relaunch the app"
