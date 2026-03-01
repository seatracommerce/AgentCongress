#!/usr/bin/env bash
# One-time setup: grant the default Compute/Cloud Build service account
# permission to deploy Cloud Run from source (fixes PERMISSION_DENIED on storage bucket).
# Run from project root. Requires project Owner or resourcemanager.projects.setIamPolicy.
#
# Usage: ./scripts/gcp-setup-build-permissions.sh [--project PROJECT_ID]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GCP_PROJECT_ID="${GCP_PROJECT_ID:-agentcongress}"
[[ "${1:-}" = "--project" ]] && { GCP_PROJECT_ID="$2"; shift 2; }

PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting Cloud Run build permissions to default compute SA..."
echo "  Project: $GCP_PROJECT_ID"
echo "  Service account: $COMPUTE_SA"
echo ""

gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/run.builder"

echo ""
echo "Done. Re-run ./scripts/deploy-backend.sh to deploy."
