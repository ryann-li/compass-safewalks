#!/usr/bin/env bash
# Local test script that uses the correct virtual environment Python

# Get the script directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$DIR")"

# Use venv Python directly to bypass conda PATH override
echo "Running local tests with venv Python..."
"$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/test_local.py"