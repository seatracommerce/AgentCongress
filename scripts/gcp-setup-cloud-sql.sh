#!/usr/bin/env bash
# Create a Cloud SQL PostgreSQL 15 instance and database for AgentCongress.
# Run once. Requires gcloud CLI. Passwords via env or prompts.
#
# Usage:
#   ./scripts/gcp-setup-cloud-sql.sh
#   ./scripts/gcp-setup-cloud-sql.sh --project agentcongress --region us-central1
#   ROOT_PASSWORD=xxx DB_APP_PASSWORD=yyy ./scripts/gcp-setup-cloud-sql.sh
#
# Options:
#   --project PROJECT_ID   (default: agentcongress)
#   --region REGION        (default: us-central1, match Cloud Run)
#   --instance NAME        (default: agentcongress-db)
#   --database NAME        (default: agentcongress)
#   --tier TIER            (default: db-f1-micro; use db-g1-small for more capacity)
#
# Passwords (set or you will be prompted):
#   ROOT_PASSWORD          postgres superuser (required for instance create)
#   DB_APP_PASSWORD        app user password (optional; if set we create user agentcongress)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

GCP_PROJECT_ID="${GCP_PROJECT_ID:-agentcongress}"
INSTANCE_NAME="${INSTANCE_NAME:-agentcongress-db}"
DB_NAME="${DB_NAME:-agentcongress}"
DB_USER="${DB_USER:-agentcongress}"
REGION="${GCP_REGION:-us-central1}"
TIER="${TIER:-db-f1-micro}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --project)   GCP_PROJECT_ID="$2"; shift 2 ;;
    --region)    REGION="$2"; shift 2 ;;
    --instance)  INSTANCE_NAME="$2"; shift 2 ;;
    --database)  DB_NAME="$2"; shift 2 ;;
    --tier)      TIER="$2"; shift 2 ;;
    *)           echo "Unknown option: $1"; exit 1 ;;
  esac
done

echo "Cloud SQL setup"
echo "  project:  $GCP_PROJECT_ID"
echo "  region:   $REGION"
echo "  instance: $INSTANCE_NAME"
echo "  database: $DB_NAME"
echo "  tier:     $TIER"
echo ""

# 1. Enable API
echo "Enabling Cloud SQL Admin API..."
gcloud services enable sqladmin.googleapis.com --project="$GCP_PROJECT_ID"

# 2. Root password (required for instance creation)
if [[ -z "${ROOT_PASSWORD:-}" ]]; then
  echo "Enter password for Cloud SQL 'postgres' (root) user (stored only in the instance):"
  read -rs ROOT_PASSWORD
  echo ""
  if [[ -z "${ROOT_PASSWORD:-}" ]]; then
    echo "ROOT_PASSWORD is required."; exit 1
  fi
  echo "Re-enter password:"
  read -rs ROOT_PASSWORD2
  echo ""
  if [[ "$ROOT_PASSWORD" != "$ROOT_PASSWORD2" ]]; then
    echo "Passwords do not match."; exit 1
  fi
fi

# 3. Create instance (PostgreSQL 15, same region as Cloud Run)
if gcloud sql instances describe "$INSTANCE_NAME" --project="$GCP_PROJECT_ID" &>/dev/null; then
  echo "Instance $INSTANCE_NAME already exists."
else
  echo "Creating Cloud SQL instance (this may take several minutes)..."
  gcloud sql instances create "$INSTANCE_NAME" \
    --project="$GCP_PROJECT_ID" \
    --database-version=POSTGRES_15 \
    --tier="$TIER" \
    --region="$REGION" \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --root-password="$ROOT_PASSWORD"
  echo "Instance created."
fi

# 4. Create database
echo ""
if gcloud sql databases describe "$DB_NAME" --instance="$INSTANCE_NAME" --project="$GCP_PROJECT_ID" &>/dev/null; then
  echo "Database $DB_NAME already exists."
else
  echo "Creating database: $DB_NAME"
  gcloud sql databases create "$DB_NAME" --instance="$INSTANCE_NAME" --project="$GCP_PROJECT_ID"
fi

# 5. Optional: create app user (if DB_APP_PASSWORD set)
if [[ -n "${DB_APP_PASSWORD:-}" ]]; then
  if gcloud sql users list --instance="$INSTANCE_NAME" --project="$GCP_PROJECT_ID" 2>/dev/null | grep -q "^$DB_USER"; then
    echo "User $DB_USER already exists (password not updated by this script)."
  else
    echo "Creating database user: $DB_USER"
    gcloud sql users create "$DB_USER" \
      --instance="$INSTANCE_NAME" \
      --password="$DB_APP_PASSWORD" \
      --project="$GCP_PROJECT_ID"
    echo "Grant the user access to the database by running once (e.g. in Cloud Shell):"
    echo "  gcloud sql connect $INSTANCE_NAME --user=postgres --database=postgres --project=$GCP_PROJECT_ID"
    echo "  Then in psql: GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER; \\\\c $DB_NAME; GRANT ALL ON SCHEMA public TO $DB_USER;"
  fi
  DB_USER_FOR_URL="$DB_USER"
  DB_PASS_FOR_URL="$DB_APP_PASSWORD"
else
  DB_USER_FOR_URL="postgres"
  DB_PASS_FOR_URL="$ROOT_PASSWORD"
  echo ""
  echo "Tip: To use a dedicated app user, re-run with DB_APP_PASSWORD=xxx to create user $DB_USER, then grant privileges as above."
fi

# 6. Connection name and DATABASE_URL
CONNECTION_NAME="$GCP_PROJECT_ID:$REGION:$INSTANCE_NAME"

echo ""
echo "--- Cloud SQL connection details ---"
echo "Connection name (for Cloud Run): $CONNECTION_NAME"
echo ""
echo "DATABASE_URL (Cloud Run with Cloud SQL connection):"
echo "  postgresql+asyncpg://$DB_USER_FOR_URL:YOUR_PASSWORD@/$DB_NAME?host=/cloudsql/$CONNECTION_NAME"
echo ""
echo "Replace YOUR_PASSWORD with the actual password (or store in Secret Manager as DATABASE_URL)."
echo ""
echo "Next steps:"
echo "  1. Add Cloud SQL connection to Cloud Run: when deploying, add the instance as a connection (e.g. deploy script or Console: Cloud Run → service → Connections → Cloud SQL → add $INSTANCE_NAME)."
echo "  2. Set DATABASE_URL in Cloud Run env or Secret Manager (use the URL above with the real password)."
echo "  3. Run migrations: connect from a machine with access (e.g. Cloud Shell or Cloud Run job) and run: alembic upgrade head"
echo ""
