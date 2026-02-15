#!/usr/bin/env bash
set -euo pipefail

# ======================================================
# DMP Hotspot - Local Dev Environment Loader
# Usage:
#   source ./dev.sh
#   flask run
# ======================================================

# --- Local DB (hard safety: never Render here) ---
export DATABASE_URL="postgresql://dmp_user:1010@127.0.0.1:5432/dmp_hotspot"

# --- Flask ---
export FLASK_APP="app"
export FLASK_DEBUG="1"
export SECRET_KEY="${SECRET_KEY:-dev-secret-change-me}"

# --- M-Pesa (sandbox by default) ---
export MPESA_ENV="${MPESA_ENV:-sandbox}"
export MPESA_CONSUMER_KEY="${MPESA_CONSUMER_KEY:-}"
export MPESA_CONSUMER_SECRET="${MPESA_CONSUMER_SECRET:-}"
export MPESA_SHORTCODE="${MPESA_SHORTCODE:-}"
export MPESA_PASSKEY="${MPESA_PASSKEY:-}"
export MPESA_CALLBACK_URL="${MPESA_CALLBACK_URL:-https://dmp-hotspot.onrender.com/api/mpesa/callback}"
export MPESA_TIMEOUT_URL="${MPESA_TIMEOUT_URL:-}"
export MPESA_STK_ACCOUNT_REF="${MPESA_STK_ACCOUNT_REF:-DmpolinConnect}"
export MPESA_STK_DESC="${MPESA_STK_DESC:-Internet subscription}"

# --- Router automation (safe defaults) ---
export ROUTER_AUTOMATION_ENABLED="${ROUTER_AUTOMATION_ENABLED:-false}"
export ROUTER_AUTOMATION_DRY_RUN="${ROUTER_AUTOMATION_DRY_RUN:-true}"

# --- Scheduler (safe defaults) ---
export SCHEDULER_ENABLED="${SCHEDULER_ENABLED:-true}"
export SCHEDULER_DRY_RUN="${SCHEDULER_DRY_RUN:-true}"
export SCHEDULER_INTERVAL_MINUTES="${SCHEDULER_INTERVAL_MINUTES:-2}"

# --- Reconciliation layer (safe defaults) ---
export RECONCILE_ENABLED="${RECONCILE_ENABLED:-true}"
export RECONCILE_INTERVAL_MINUTES="${RECONCILE_INTERVAL_MINUTES:-3}"
export RECONCILE_PENDING_AFTER_SECONDS="${RECONCILE_PENDING_AFTER_SECONDS:-180}"
export RECONCILE_TIMEOUT_SECONDS="${RECONCILE_TIMEOUT_SECONDS:-1800}"
export RECONCILE_MAX_ATTEMPTS="${RECONCILE_MAX_ATTEMPTS:-10}"
export ACTIVATION_RETRY_MAX="${ACTIVATION_RETRY_MAX:-5}"

# --- MikroTik Lab/Local ---
export MIKROTIK_PPPOE_HOST="${MIKROTIK_PPPOE_HOST:-192.168.230.1}"
export MIKROTIK_PPPOE_PORT="${MIKROTIK_PPPOE_PORT:-8728}"
export MIKROTIK_PPPOE_USER="${MIKROTIK_PPPOE_USER:-admin}"
export MIKROTIK_PPPOE_PASS="${MIKROTIK_PPPOE_PASS:-9Dmpolin}"
export MIKROTIK_PPPOE_TLS="${MIKROTIK_PPPOE_TLS:-false}"

export MIKROTIK_HOTSPOT_HOST="${MIKROTIK_HOTSPOT_HOST:-192.168.240.1}"
export MIKROTIK_HOTSPOT_PORT="${MIKROTIK_HOTSPOT_PORT:-8728}"
export MIKROTIK_HOTSPOT_USER="${MIKROTIK_HOTSPOT_USER:-admin}"
export MIKROTIK_HOTSPOT_PASS="${MIKROTIK_HOTSPOT_PASS:-9Dmpolin}"
export MIKROTIK_HOTSPOT_TLS="${MIKROTIK_HOTSPOT_TLS:-false}"

echo "✅ Loaded DMP Hotspot local dev environment"
echo "   DATABASE_URL=$DATABASE_URL"
echo "   SCHEDULER_ENABLED=$SCHEDULER_ENABLED  SCHEDULER_DRY_RUN=$SCHEDULER_DRY_RUN"
echo "   RECONCILE_ENABLED=$RECONCILE_ENABLED"
echo "   ROUTER_AUTOMATION_ENABLED=$ROUTER_AUTOMATION_ENABLED  ROUTER_AUTOMATION_DRY_RUN=$ROUTER_AUTOMATION_DRY_RUN"
