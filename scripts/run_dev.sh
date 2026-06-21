#!/usr/bin/env bash
set -euo pipefail

uv run uvicorn autoapply_agent.main:app --reload
