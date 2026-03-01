#!/usr/bin/env bash
#
# Deploy the AgentCongress backend to Google Cloud Run.
# Run from the project root. Requires: gcloud CLI, Docker (for local build), or Cloud Build.
#
# Usage:
#   ./scripts/deploy-backend.sh
#   ./scripts/deploy-backend.sh --project my-project --region us-central1
#   ./scripts/deploy-backend.sh --env-vars-file .env.production
#
# Optional env (or flags):
#   GCP_PROJECT_ID       - GCP project (default: gcloud config get-value project)
#   GCP_REGION           - Cloud Run region (default: us-central1)
#   SERVICE_NAME         - Cloud Run service name (default: agentcongress-backend)
#   ENV_VARS_FILE        - Path to KEY=VALUE file for --env-vars-file (optional)
#   CLOUD_SQL_INSTANCE   - Connection name PROJECT:REGION:INSTANCE to add Cloud SQL (optional)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

# Defaults (project: agentcongress, region: us-central1; override with GCP_PROJECT_ID or --project)
GCP_PROJECT_ID="${GCP_PROJECT_ID:-agentcongress}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-agentcongress-backend}"
ENV_VARS_FILE="${ENV_VARS_FILE:-}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-900}"
MEMORY="${MEMORY:-1Gi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-2}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-}"

# Parse optional flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)
      GCP_PROJECT_ID="$2"
      shift 2
      ;;
    --region)
      GCP_REGION="$2"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="$2"
      shift 2
      ;;
    --env-vars-file)
      ENV_VARS_FILE="$2"
      shift 2
      ;;
    --cloud-sql-instance)
      CLOUD_SQL_INSTANCE="$2"
      shift 2
      ;;
    --timeout)
      REQUEST_TIMEOUT="$2"
      shift 2
      ;;
    --memory)
      MEMORY="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--project PROJECT] [--region REGION] [--service-name NAME] [--env-vars-file PATH] [--cloud-sql-instance PROJECT:REGION:INSTANCE] [--timeout SECS] [--memory SIZE]"
      echo "Deploy backend to Cloud Run. Env vars can also be set via ENV_VARS_FILE or .env.production."
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Allow gcloud config to override default project if not explicitly set via env/flag
if [[ -z "$GCP_PROJECT_ID" ]]; then
  GCP_PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
fi
if [[ -z "$GCP_PROJECT_ID" ]]; then
  echo "Error: GCP_PROJECT_ID not set. Set GCP_PROJECT_ID or run: gcloud config set project PROJECT_ID" >&2
  exit 1
fi

# Optional: env file for Cloud Run. gcloud expects YAML (values with ':' must be quoted).
# We convert KEY=VALUE .env format to a temp YAML file so colons in e.g. DATABASE_URL don't break parsing.
ENV_ARGS=()
SRC_ENV=""
if [[ -n "$ENV_VARS_FILE" && -f "$ENV_VARS_FILE" ]]; then
  SRC_ENV="$ENV_VARS_FILE"
elif [[ -f "$REPO_ROOT/.env.production" ]]; then
  SRC_ENV="$REPO_ROOT/.env.production"
fi
if [[ -n "$SRC_ENV" ]]; then
  GCLOUD_ENV_YAML="$(mktemp)"
  trap 'rm -f "$GCLOUD_ENV_YAML"' EXIT
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" ]] && continue
    if [[ "$line" == *=* ]]; then
      key="${line%%=*}"
      key="${key%"${key##*[![:space:]]}"}"
      val="${line#*=}"
      val="${val#\"}"; val="${val%\"}"
      val="${val//\\/\\\\}"; val="${val//\"/\\\"}"
      echo "${key}: \"${val}\"" >> "$GCLOUD_ENV_YAML"
    fi
  done < "$SRC_ENV"
  ENV_ARGS+=(--env-vars-file="$GCLOUD_ENV_YAML")
fi

echo "Deploying backend to Cloud Run..."
echo "  Project:  $GCP_PROJECT_ID"
echo "  Region:   $GCP_REGION"
echo "  Service:  $SERVICE_NAME"
echo "  Timeout:  ${REQUEST_TIMEOUT}s"
echo "  Memory:   $MEMORY"
[[ -n "$SRC_ENV" ]] && echo "  Env file: $SRC_ENV"
echo ""

cd "$REPO_ROOT"

# Build gcloud args; avoid empty array expansion under set -u
DEPLOY_ARGS=(
  --project="$GCP_PROJECT_ID"
  --region="$GCP_REGION"
  --source="$BACKEND_DIR"
  --timeout="$REQUEST_TIMEOUT"
  --memory="$MEMORY"
  --min-instances="$MIN_INSTANCES"
  --max-instances="$MAX_INSTANCES"
  --allow-unauthenticated
)
[[ -n "${CLOUD_SQL_INSTANCE:-}" ]] && DEPLOY_ARGS+=(--add-cloudsql-instances="$CLOUD_SQL_INSTANCE") && echo "  Cloud SQL: $CLOUD_SQL_INSTANCE"
[[ ${#ENV_ARGS[@]} -gt 0 ]] && DEPLOY_ARGS+=("${ENV_ARGS[@]}")

gcloud run deploy "$SERVICE_NAME" "${DEPLOY_ARGS[@]}"

echo ""
echo "Done. Service URL:"
gcloud run services describe "$SERVICE_NAME" --project="$GCP_PROJECT_ID" --region="$GCP_REGION" --format='value(status.url)'
