#!/usr/bin/env bash
# Runs the API tests against the PHP backend using a throwaway database.
# The committed hospital.db* files are never touched.
# Optional: PHP_BIN=/path/to/php PORT=8000
set -u
cd "$(dirname "$0")/.."
PHP_BIN=${PHP_BIN:-php}
PORT=${PORT:-8000}
SCRATCH=$(mktemp -d "${PWD}/.scratch-XXXXXX")
trap 'kill $SRV 2>/dev/null; rm -rf "$SCRATCH"' EXIT

"$PHP_BIN" -v | head -1
for f in php/*.php api/*.php; do "$PHP_BIN" -l "$f" || exit 1; done

# A missing DB file is created from schema.sql (schema plus seed data).
OCCUAID_DB="$SCRATCH/test.db" "$PHP_BIN" -S "localhost:$PORT" php/router.php >"$SCRATCH/server.log" 2>&1 &
SRV=$!
sleep 1

echo "--- tests/php-api.test.mjs"
BASE="http://localhost:$PORT" node tests/php-api.test.mjs
STATUS=$?
exit $STATUS
