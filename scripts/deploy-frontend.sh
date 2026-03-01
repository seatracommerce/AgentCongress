#!/usr/bin/env bash
#
# Deploy the AgentCongress Next.js frontend to Vercel or Google Cloud Run.
# Run from the project root. Requires: NEXT_PUBLIC_API_URL (backend URL).
#
# Usage:
#   NEXT_PUBLIC_API_URL=https://your-backend.run.app ./scripts/deploy-frontend.sh vercel
#   NEXT_PUBLIC_API_URL=https://your-backend.run.app ./scripts/deploy-frontend.sh cloudrun
#   ./scripts/deploy-frontend.sh vercel --api-url https://your-backend.run.app
#
# Targets:
#   vercel    - Deploy to Vercel (requires Vercel CLI: npm i -g vercel). Uses free tier.
#   cloudrun  - Build and deploy to Cloud Run (requires gcloud CLI). Same GCP project as backend.
#
# Options (before target):
#   --api-url URL   Backend API URL (sets NEXT_PUBLIC_API_URL at build time). Required if not in env.
#   --project ID    (Cloud Run only) GCP project (default: agentcongress)
#   --region REGION (Cloud Run only) Region (default: us-central1)
#   --service-name  (Cloud Run only) Service name (default: agentcongress-frontend)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

# Defaults
GCP_PROJECT_ID="${GCP_PROJECT_ID:-agentcongress}"
GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-agentcongress-frontend}"
API_URL="${NEXT_PUBLIC_API_URL:-}"

# Parse all args (options and target in any order)
TARGET=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --api-url)
      API_URL="$2"
      shift 2
      ;;
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
    --help|-h)
      echo "Usage: $0 [--api-url URL] [--project PROJECT] [--region REGION] [--service-name NAME] vercel|cloudrun"
      echo "  vercel   - Deploy to Vercel (set NEXT_PUBLIC_API_URL or --api-url)"
      echo "  cloudrun - Deploy to Cloud Run"
      exit 0
      ;;
    vercel|cloudrun)
      TARGET="$1"
      shift 1
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 [options] vercel|cloudrun" >&2
  echo "  Use --help for details." >&2
  exit 1
fi

# NEXT_PUBLIC_API_URL is required at build time for Cloud Run; for Vercel set it in project env
if [[ "$TARGET" == "cloudrun" && -z "$API_URL" ]]; then
  echo "Error: For Cloud Run, set NEXT_PUBLIC_API_URL or pass --api-url (your backend API base URL)." >&2
  exit 1
fi

export NEXT_PUBLIC_API_URL="$API_URL"
echo "Deploying frontend (target: $TARGET)"
[[ -n "$API_URL" ]] && echo "  NEXT_PUBLIC_API_URL=$API_URL"
echo ""

if [[ "$TARGET" == "vercel" ]]; then
  if ! command -v vercel &>/dev/null; then
    echo "Vercel CLI not found. Install with: npm i -g vercel" >&2
    exit 1
  fi
  echo "Ensure NEXT_PUBLIC_API_URL is set in Vercel (Project Settings -> Environment Variables) for Production, or the build will not have your backend URL."
  cd "$FRONTEND_DIR"
  vercel --prod
  echo ""
  echo "Done. Frontend is live on Vercel. Set your backend WEBAPP_URL/CORS if needed."

elif [[ "$TARGET" == "cloudrun" ]]; then
  if ! command -v gcloud &>/dev/null; then
    echo "gcloud CLI not found." >&2
    exit 1
  fi
  # Next.js reads .env.production.local at build time. Create it so Cloud Build gets it.
  ENV_FILE="$FRONTEND_DIR/.env.production.local"
  echo "NEXT_PUBLIC_API_URL=$API_URL" > "$ENV_FILE"
  trap 'rm -f "$ENV_FILE"' EXIT

  echo "Building and deploying to Cloud Run..."
  gcloud run deploy "$SERVICE_NAME" \
    --project="$GCP_PROJECT_ID" \
    --region="$GCP_REGION" \
    --source="$FRONTEND_DIR" \
    --allow-unauthenticated \
    --port=8080

  echo ""
  echo "Done. Service URL:"
  gcloud run services describe "$SERVICE_NAME" --project="$GCP_PROJECT_ID" --region="$GCP_REGION" --format='value(status.url)'
else
  echo "Unknown target: $TARGET. Use vercel or cloudrun." >&2
  exit 1
fi
