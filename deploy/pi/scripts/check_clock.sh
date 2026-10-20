#!/usr/bin/env bash
# In tình trạng đồng bộ giờ của Pi để điền clock_synced và kiểm T26 (reboot không Internet).
# Dùng:  bash deploy/pi/scripts/check_clock.sh
set -uo pipefail

echo "== timedatectl"
timedatectl show -p NTPSynchronized -p TimeUSec -p Timezone 2>&1 || true

echo "== chronyc tracking"
if command -v chronyc >/dev/null 2>&1; then
  chronyc tracking 2>&1 || true
  echo "== chronyc sources"
  chronyc sources -v 2>&1 || true
else
  echo "chrony chưa được cài (sudo apt install chrony)"
fi

synced=$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo unknown)
echo
echo "NTPSynchronized=${synced}"
[[ $synced == yes ]]
