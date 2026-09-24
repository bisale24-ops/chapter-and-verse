#!/bin/sh
# One command: start the page on http://localhost:8000
export PYTHONPATH="$(dirname "$0")/src"
exec python3 -m chapterverse.server "${1:-8000}"
