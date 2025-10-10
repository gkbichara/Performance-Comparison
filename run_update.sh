#!/bin/bash

# Football Performance Comparison - Automated Update Script
# Runs scraper and analysis with logging

# Set project directory
PROJECT_DIR="/Users/gkb/Desktop/Performance-Comparison"
cd "$PROJECT_DIR" || exit 1

# Create logs directory if it doesn't exist
mkdir -p logs

# Log file with timestamp
LOG_FILE="logs/update_$(date +%Y%m%d_%H%M%S).log"

echo "=====================================================" >> "$LOG_FILE"
echo "Football Performance Comparison - Update Started" >> "$LOG_FILE"
echo "Time: $(date)" >> "$LOG_FILE"
echo "=====================================================" >> "$LOG_FILE"

# Activate virtual environment
source venv/bin/activate

# Run scraper to fetch latest data
echo -e "\n[1/2] Running scraper..." >> "$LOG_FILE"
python scraper.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Scraper completed successfully" >> "$LOG_FILE"
else
    echo "✗ Scraper failed" >> "$LOG_FILE"
    exit 1
fi

# Run analysis
echo -e "\n[2/2] Running analysis..." >> "$LOG_FILE"
python analysis.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Analysis completed successfully" >> "$LOG_FILE"
else
    echo "✗ Analysis failed" >> "$LOG_FILE"
    exit 1
fi

echo -e "\n=====================================================" >> "$LOG_FILE"
echo "Update Completed Successfully" >> "$LOG_FILE"
echo "Time: $(date)" >> "$LOG_FILE"
echo "=====================================================" >> "$LOG_FILE"

# Keep only last 10 log files
cd logs
ls -t update_*.log | tail -n +11 | xargs rm -f 2>/dev/null

exit 0

