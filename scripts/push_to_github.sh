#!/usr/bin/env bash
# Create the GitHub repository (API) and push. Needs a PAT with "repo" scope.
#
#   export GITHUB_USERNAME="your_github_login"
#   export GITHUB_TOKEN="ghp_xxxxxxxx"
#   cd /path/to/invertebrate-reference-genome-pipeline
#   bash scripts/push_to_github.sh
#
set -euo pipefail

REPO_NAME="${GITHUB_REPO_NAME:-invertebrate-reference-genome-pipeline}"

if [[ -z "${GITHUB_USERNAME:-}" || -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Set GITHUB_USERNAME and GITHUB_TOKEN, then re-run." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .git ]]; then
  echo "[FATAL] .git not found in $ROOT" >&2
  exit 1
fi

BRANCH="$(git branch --show-current)"
if [[ -z "$BRANCH" ]]; then
  echo "[FATAL] No current branch." >&2
  exit 1
fi

HTTP_CODE=$(curl -sS -o /tmp/gh_repo.json -w "%{http_code}" \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${GITHUB_USERNAME}/${REPO_NAME}")

if [[ "$HTTP_CODE" == "404" ]]; then
  echo "[INFO] Creating https://github.com/${GITHUB_USERNAME}/${REPO_NAME} ..."
  JSON=$(printf '{"name":"%s","private":false,"auto_init":false}' "$REPO_NAME")
  curl -sS -X POST \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    https://api.github.com/user/repos \
    -d "$JSON" | head -c 400
  echo
elif [[ "$HTTP_CODE" == "200" ]]; then
  echo "[INFO] Repository already exists."
else
  echo "[FATAL] GitHub API HTTP ${HTTP_CODE}" >&2
  cat /tmp/gh_repo.json >&2
  exit 1
fi

echo "[INFO] Pushing branch ${BRANCH} ..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
git push "https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${REPO_NAME}.git" "$BRANCH"
git branch --set-upstream-to="origin/$BRANCH" "$BRANCH" 2>/dev/null || true

echo "[OK] https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
