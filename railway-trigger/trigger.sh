#!/bin/sh
# Run by the Railway cron service "trigger" (schedule "4,34 13-22 * * *", in UTC, set in the
# service settings). Starts the "Check for new videos" workflow, but only from 15:00 to
# midnight, Paris time, so the same UTC schedule works in summer and winter time.
# GITHUB_TOKEN: fine-grained token with "Actions: read and write" on corbiiy/yt-checker.
set -eu

hour=$(TZ=Europe/Paris date +%H)
hour=${hour#0}
if [ "$hour" -lt 15 ]; then
  echo "Skipped: ${hour}h in Paris, outside 15:00-24:00"
  exit 0
fi

# A pasted token can carry a stray newline or space, which would break the header.
: "${GITHUB_TOKEN:?GITHUB_TOKEN is not set}"
token=$(printf %s "$GITHUB_TOKEN" | tr -d '[:space:]')
curl -fsS -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $token" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d '{"ref":"main"}' \
  https://api.github.com/repos/corbiiy/yt-checker/actions/workflows/check.yml/dispatches
echo "Check started (${hour}h in Paris)"
