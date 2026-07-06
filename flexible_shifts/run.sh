#!/usr/bin/with-contenv bashio
set -e

export TZ="$(bashio::config 'timezone')"
export SHIFT_MANAGER_DB="/data/flexible_shifts.db"
export SHIFT_MANAGER_HA_SYNC="$(bashio::config 'home_assistant_sync')"
export SHIFT_MANAGER_SYNC_INTERVAL="$(bashio::config 'sync_interval_seconds')"
export SHIFT_MANAGER_INGRESS_ONLY="true"

exec python3 /app/main.py
