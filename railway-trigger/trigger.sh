#!/bin/sh
# Run by the Railway cron service "trigger" (schedule "4,34 7-22 * * *", in UTC, set in the
# service settings). Starts the "Check for new videos" workflow, but only until midnight, Paris
# time, from 15:00 on weekdays and from 9:00 at the weekend, so the same UTC schedule works in
# summer and winter time. CHECK_FROM in site/index.html must match.
# GITHUB_TOKEN: fine-grained token with "Actions: read and write" on corbiiy/yt-checker.
set -eu

# Day (1 = Monday ... 7 = Sunday) and hour in Paris, read at once so midnight can't fall between.
set -- $(TZ=Europe/Paris date '+%u %H')
day=$1
hour=${2#0}
from=15
if [ "$day" -ge 6 ]; then from=9; fi
if [ "$hour" -lt "$from" ]; then
  echo "Skipped: ${hour}h in Paris, outside ${from}:00-24:00"
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
