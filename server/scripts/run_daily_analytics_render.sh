#!/bin/bash
# Daily Analytics Pipeline Runner for Render
# This script runs the daily analytics pipeline in the Render environment

set -e  # Exit on any error

echo "Starting Daily Analytics Pipeline at $(date)"
echo "========================================"

# Change to the scripts directory
cd "$(dirname "$0")"

# Set Python path for imports
export PYTHONPATH="${PYTHONPATH}:/opt/render/project/src/server"

# Run the analytics pipeline
python3 run_daily_analytics.py

echo "========================================"
echo "Daily Analytics Pipeline completed at $(date)"