#!/bin/bash
# TradeWizard Startup Script

cd "$(dirname "$0")/backend"

# Install dependencies if needed
if ! python -c "import anthropic" 2>/dev/null; then
  echo "Installing dependencies..."
  pip install -r requirements.txt
fi

# Copy .env if it doesn't exist
if [ ! -f ../.env ] && [ -f ../.env.example ]; then
  cp ../.env.example ../.env
  echo "Created .env from .env.example — please add your ANTHROPIC_API_KEY"
fi

# Load .env
if [ -f ../.env ]; then
  export $(grep -v '^#' ../.env | xargs)
fi

echo "Starting TradeWizard at http://localhost:${PORT:-8000}"
python main.py
