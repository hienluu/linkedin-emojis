#!/usr/bin/env bash
# Deploy to Google Cloud Run.
#
#   ./deploy_gcp.sh
#
# Builds remotely with Cloud Build (no local Docker needed) and deploys a
# scale-to-zero service. If a Secret Manager secret named $SECRET exists, it is
# mounted as LLM_API_KEY and LLM mode is enabled; otherwise the app deploys
# rules-only and the LLM button stays disabled.
set -euo pipefail

PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-$(gcloud config get-value run/region 2>/dev/null || echo us-west1)}"
SERVICE="${SERVICE:-linkedin-emoji-search}"
SECRET="${SECRET:-llm-api-key}"

echo "project=$PROJECT  region=$REGION  service=$SERVICE"

args=(
  --source .
  --project "$PROJECT"
  --region "$REGION"
  --platform managed
  --allow-unauthenticated          # public, like the Modal endpoint
  --port 8080
  --memory 512Mi
  --cpu 1
  --min-instances 0                # scale to zero: no idle cost
  --max-instances 5
  --concurrency 80
  --timeout 120
)

# Mount the key only if the secret actually exists, so a first deploy works
# before any secret has been created.
if gcloud secrets describe "$SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  echo "found secret '$SECRET' -> enabling LLM mode"
  args+=(--set-secrets "LLM_API_KEY=${SECRET}:latest")

  # The runtime service account must be able to read the secret. gcloud does not
  # grant this automatically — without it the revision fails to start.
  SA="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
  gcloud secrets add-iam-policy-binding "$SECRET" --project "$PROJECT" \
    --member="serviceAccount:${SA}" --role="roles/secretmanager.secretAccessor" \
    >/dev/null 2>&1 && echo "  granted secretAccessor to ${SA}"

  # Base URL and model are not sensitive, so they travel as plain env vars.
  # NOTE: repeating --set-env-vars replaces rather than appends, so build one
  # comma-separated value.
  envs=()
  [[ -n "${LLM_BASE_URL:-}" ]] && envs+=("LLM_BASE_URL=${LLM_BASE_URL}")
  [[ -n "${LLM_MODEL:-}"    ]] && envs+=("LLM_MODEL=${LLM_MODEL}")
  if ((${#envs[@]})); then
    args+=(--set-env-vars "$(IFS=,; echo "${envs[*]}")")
  else
    echo "  WARNING: LLM_MODEL not provided — LLM mode needs it and will stay disabled."
    echo "           LLM_BASE_URL=... LLM_MODEL=... ./deploy_gcp.sh"
  fi
else
  echo "no secret '$SECRET' -> deploying rules-only (LLM button disabled)"
  echo "  to enable later:"
  echo "    printf %s \"\$YOUR_KEY\" | gcloud secrets create $SECRET --data-file=- --project $PROJECT"
  echo "    LLM_BASE_URL=... LLM_MODEL=... ./deploy_gcp.sh"
fi

gcloud run deploy "$SERVICE" "${args[@]}"

URL=$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
        --format='value(status.url)')
echo
echo "deployed: $URL"
curl -fsS "$URL/api/health" && echo
