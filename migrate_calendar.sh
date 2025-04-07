#!/bin/bash
# Shell script to manage calendar database migrations
# This script will attempt to run migrations_calendar.py first,
# and will fall back to direct_calendar_migration.py if the first one fails

echo "Starting calendar migration process..."

# Try the SQLAlchemy-based migration first
echo "Attempting SQLAlchemy-based migration..."
python migrations_calendar.py

# Check if migration succeeded
if [ $? -eq 0 ]; then
    echo "SQLAlchemy migration completed successfully."
    exit 0
else
    echo "SQLAlchemy migration failed, falling back to direct SQL migration..."
    
    # Try direct SQL migration as fallback
    echo "Attempting direct SQL migration..."
    python direct_calendar_migration.py
    
    # Check if fallback migration succeeded
    if [ $? -eq 0 ]; then
        echo "Direct SQL migration completed successfully."
        exit 0
    else
        echo "Both migration methods failed. Please check the logs for details."
        exit 1
    fi
fi
