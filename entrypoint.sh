#!/bin/sh

# Ensure the database directory and files are owned by the non-root user
if [ -d "/app/data" ]; then
    chown -R appuser:appgroup /app/data
fi

# Run the application as the non-root user
exec /usr/sbin/runuser -u appuser -- python main.py
