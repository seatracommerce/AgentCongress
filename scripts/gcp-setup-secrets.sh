#!/usr/bin/env bash
# Create Secret Manager secrets and grant Cloud Run access. Run once before using ENV=production.
# After running, add your real API keys as secret versions in the GCP Console (Secret Manager).
#
# Usage: ./scripts/gcp-setup-secrets.sh [--project PROJECT_ID]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GCP_PROJECT_ID="${GCP_PROJECT_ID:-agentcongress}"
[[ "${1:-}" = "--project" ]] && { GCP_PROJECT_ID="$2"; shift 2; }

# Secrets the backend expects when ENV=production (config.py resolve_secrets)
SECRET_NAMES=(
  ANTHROPIC_API_KEY
  CONGRESS_API_KEY
  TWITTER_API_KEY
  TWITTER_API_SECRET
  TWITTER_ACCESS_TOKEN
  TWITTER_ACCESS_SECRET
)

echo "Secret Manager setup for project: $GCP_PROJECT_ID"
echo ""

# 1. Enable API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project="$GCP_PROJECT_ID"

# 2. Grant Cloud Run (default compute SA) permission to read secrets
PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo ""
echo "Granting Cloud Run service account access to Secret Manager..."
gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --project="$GCP_PROJECT_ID"

# 3. Create each secret with a placeholder (you'll add a new version with the real key in the Console)
echo ""
for name in "${SECRET_NAMES[@]}"; do
  if gcloud secrets describe "$name" --project="$GCP_PROJECT_ID" &>/dev/null; then
    echo "  $name (already exists)"
  else
    echo "  Creating secret: $name"
    printf '%s' "replace-me" | gcloud secrets create "$name" \
      --data-file=- \
      --project="$GCP_PROJECT_ID" \
      --replication-policy=automatic
  fi
done

echo ""
echo "Done. Next steps:"
echo "  1. In GCP Console → Secret Manager, open each secret and add a new version with your real API key value."
echo "  2. Set Cloud Run env vars: ENV=production, GCP_PROJECT_ID=$GCP_PROJECT_ID (and others as needed)."
echo "  3. Redeploy or restart the Cloud Run service so it reads from Secret Manager."
