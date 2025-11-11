#!/bin/bash
# Daily Analytics Pipeline Runner
# This script runs the daily analytics pipeline using the Python virtual environment

echo "Starting Daily Analytics Pipeline at $(date)"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the Python virtual environment and run the pipeline
source .venv311/bin/activate && python run_daily_analytics.py

# Check exit code
if [ $? -eq 0 ]; then
    echo "Daily Analytics Pipeline completed successfully at $(date)"
else
    echo "Daily Analytics Pipeline completed with errors at $(date)"
    exit 1
fi