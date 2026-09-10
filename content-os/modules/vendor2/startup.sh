#!/bin/sh
set -eu
cd "$(dirname "$0")"
export CONTENT_OS_MODE="${CONTENT_OS_MODE:-MOCK}"
export PORT="${PORT:-8080}"

if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/healthz"; then
  exit 0
fi

if [ ! -d node_modules ]; then
  npm ci
fi

npm run dev >> /tmp/thbison-content-os-dev.log 2>&1 &

i=0
while [ "$i" -lt 90 ]; do
  if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/healthz"; then
    exit 0
  fi
  i=$((i + 1))
  sleep 1
done

echo "content-os failed to become healthy on port ${PORT}" >&2
exit 1
