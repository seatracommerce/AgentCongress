#!/usr/bin/env bash
# Create the Cloud Tasks queue and grant the Cloud Run service account permission to enqueue.
# Run once when using Option A2 (Cloud Run + Cloud Tasks). Run from project root.
#
# Usage: ./scripts/gcp-setup-cloud-tasks.sh [--project PROJECT_ID] [--region REGION] [--queue-name NAME]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GCP_PROJECT_ID="${GCP_PROJECT_ID:-agentcongress}"
GCP_REGION="${GCP_REGION:-us-central1}"
QUEUE_NAME="${CLOUD_TASKS_QUEUE_NAME:-agentcongress}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --project)   GCP_PROJECT_ID="$2"; shift 2 ;;
    --region)    GCP_REGION="$2";     shift 2 ;;
    --queue-name) QUEUE_NAME="$2";    shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

echo "Cloud Tasks setup"
echo "  Project: $GCP_PROJECT_ID"
echo "  Region:  $GCP_REGION"
echo "  Queue:   $QUEUE_NAME"
echo ""

# 1. Enable Cloud Tasks API
echo "Enabling Cloud Tasks API..."
gcloud services enable cloudtasks.googleapis.com --project="$GCP_PROJECT_ID"

# 2. Create the queue (idempotent: will fail if already exists; that's ok)
echo ""
echo "Creating queue ${QUEUE_NAME}..."
if gcloud tasks queues create "$QUEUE_NAME" \
  --location="$GCP_REGION" \
  --project="$GCP_PROJECT_ID" 2>/dev/null; then
  echo "  Queue created."
else
  echo "  Queue already exists or create failed (may need to delete and recreate). Continuing..."
fi

# 3. Grant the default Compute / Cloud Run service account permission to enqueue
PROJECT_NUMBER="$(gcloud projects describe "$GCP_PROJECT_ID" --format='value(projectNumber)')"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
QUEUE_ID="projects/${GCP_PROJECT_ID}/locations/${GCP_REGION}/queues/${QUEUE_NAME}"

echo ""
echo "Granting Cloud Run service account permission to enqueue tasks..."
echo "  Service account: $COMPUTE_SA"
echo "  Role: roles/cloudtasks.enqueuer"
gcloud tasks queues add-iam-policy-binding "$QUEUE_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/cloudtasks.enqueuer" \
  --project="$GCP_PROJECT_ID"

echo ""
echo "Done. Set these env vars on your Cloud Run backend (or in .env.production):"
echo "  CLOUD_TASKS_PROJECT_ID=$GCP_PROJECT_ID"
echo "  CLOUD_TASKS_LOCATION=$GCP_REGION"
echo "  CLOUD_TASKS_QUEUE_NAME=$QUEUE_NAME"
echo "  SERVICE_URL=https://agentcongress-backend-k3u7dfffua-uc.a.run.app"
echo ""
echo "Then point Cloud Scheduler at POST /admin/schedule-poll (not /admin/trigger-poll)."
