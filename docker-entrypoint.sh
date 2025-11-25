#!/bin/bash
set -e

echo "Starting QnA Agent API..."

# Start the application
echo "Starting uvicorn server..."
exec poetry run uvicorn main:application --host 0.0.0.0 --port 8000
