#!/bin/bash

# Football Performance Comparison - Automated Update Script
# Runs the full data pipeline via main.py

# Set environment for cron compatibility
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export SHELL="/bin/bash"

# Set project directory
PROJECT_DIR="/Users/gkb/Desktop/Performance-Comparison"
cd "$PROJECT_DIR" || exit 1

# Create logs directory if it doesn't exist
mkdir -p logs

# Log file with timestamp
LOG_FILE="logs/update_$(date +%Y%m%d_%H%M%S).log"

# Use absolute path to Python in virtual environment
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"

# Check if virtual environment exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "ERROR: Python virtual environment not found at $PYTHON_BIN" >> "$LOG_FILE"
    exit 1
fi

# Redirect all output to log file
{
    echo "====================================================="
    echo "Football Performance Comparison - Auto Update"
    echo "Time: $(date)"
    echo "Python: $PYTHON_BIN"
    echo "====================================================="

    # Run the main orchestrator
    "$PYTHON_BIN" -m src.main

    if [ $? -eq 0 ]; then
        echo "✓ Pipeline executed successfully"
    else
        echo "✗ Pipeline encountered errors"
        # We don't exit here because main.py handles its own errors mostly,
        # but if it crashes entirely, we want to know.
    fi

    echo ""
    echo "====================================================="
    echo "Update Process Finished"
    echo "Time: $(date)"
    echo "====================================================="

} >> "$LOG_FILE" 2>&1

# Keep only last 10 log files
cd logs
ls -t update_*.log | tail -n +11 | xargs rm -f 2>/dev/null

exit 0