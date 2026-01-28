#!/usr/bin/env bash
set -euo pipefail

set -a
[ -f .env ] && source .env
set +a

uvicorn api.index:app --reload
