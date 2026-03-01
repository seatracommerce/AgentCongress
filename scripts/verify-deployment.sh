#!/usr/bin/env bash
# Post-deploy verification: hit /health, /ready (DB), /admin/check-congress, /admin/check-twitter.
#
# Usage:
#   ./scripts/verify-deployment.sh https://agentcongress-backend-xxxx.run.app
#   SCHEDULER_SECRET=your-secret ./scripts/verify-deployment.sh https://agentcongress-backend-xxxx.run.app
#
# If SCHEDULER_SECRET is set, the script sends it as X-Scheduler-Secret for the admin check endpoints.

set -euo pipefail

BASE_URL="${1:-}"
BASE_URL="${BASE_URL%/}"
SCHEDULER_SECRET="${SCHEDULER_SECRET:-}"

if [[ -z "$BASE_URL" ]]; then
  echo "Usage: $0 BASE_URL [e.g. https://agentcongress-backend-xxxx.run.app]" >&2
  exit 1
fi

CURL_OPTS=(--silent --show-error --max-time 30)

pass=0
fail=0

check() {
  local name="$1"
  local url="$2"
  shift 2
  local tmp
  tmp="$(mktemp)"
  local code
  local -a args=("${CURL_OPTS[@]}" -w "%{http_code}" -o "$tmp" "$url")
  [[ -n "${SCHEDULER_SECRET:-}" ]] && args=("${CURL_OPTS[@]}" -H "X-Scheduler-Secret: $SCHEDULER_SECRET" -w "%{http_code}" -o "$tmp" "$url")
  code="$(curl "${args[@]}")"
  local resp
  resp="$(cat "$tmp")"
  rm -f "$tmp"
  if [[ "$code" == "200" ]] && echo "$resp" | grep -q '"status":\s*"ok"'; then
    echo "  OK   $name"
    ((pass++)) || true
    return 0
  fi
  echo "  FAIL $name (HTTP $code)"
  echo "$resp" | head -5
  if [[ "$code" == "401" ]] && echo "$resp" | grep -qi "scheduler-secret"; then
    echo "       Hint: if SCHEDULER_SECRET is set, run: SCHEDULER_SECRET=your-secret $0 $BASE_URL"
  fi
  ((fail++)) || true
  return 1
}

echo "Verifying deployment at $BASE_URL"
echo ""

check "Health (liveness)"        "$BASE_URL/health"
check "Ready (DB / Neon)"        "$BASE_URL/ready"
check "Secret Manager"           "$BASE_URL/admin/check-secrets"
check "Congress.gov API"         "$BASE_URL/admin/check-congress"
check "Twitter/X API"            "$BASE_URL/admin/check-twitter"

echo ""
if [[ $fail -gt 0 ]]; then
  echo "Result: $pass passed, $fail failed"
  exit 1
fi
echo "Result: all $pass checks passed."
