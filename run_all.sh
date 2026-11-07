#!/usr/bin/env bash
# One-command pipeline (Linux/macOS/Git Bash). Equivalent to: python run_all.py
set -euo pipefail
cd "$(dirname "$0")"
python run_all.py "$@"
