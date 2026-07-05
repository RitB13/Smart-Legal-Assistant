#!/bin/bash
set -e

echo ""
echo "========================================"
echo "  Smart Legal Assistant — Starting up"
echo "========================================"
echo ""

echo ">>> Step 1: Downloading large models from HF Hub..."
python download_models.py

echo ""
echo ">>> Step 2: Starting API server..."
exec uvicorn app:app --host 0.0.0.0 --port 7860
