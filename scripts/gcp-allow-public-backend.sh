#!/usr/bin/env bash
# Allow unauthenticated (public) access to the Cloud Run backend. Run once if you get 403 when opening the service URL.
#
# Usage: ./scripts/gcp-allow-public-backend.sh [--project PROJECT_ID] [--region REGION]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GCP_PROJECT_ID="${GCP_PROJECT_ID:-agentcongress}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-agentcongress-backend}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --project)   GCP_PROJECT_ID="$2"; shift 2 ;;
    --region)    GCP_REGION="$2"; shift 2 ;;
    *)           echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

echo "Granting allUsers roles/run.invoker on $SERVICE_NAME ($GCP_PROJECT_ID / $GCP_REGION)..."
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
  --project="$GCP_PROJECT_ID" \
  --region="$GCP_REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"

echo ""
echo "Done. The backend URL should now be publicly reachable (no auth)."
