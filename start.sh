#!/bin/bash

set -euo pipefail
trap 'echo -e "\n🛑 Interrupted. Exiting..."; exit 1' INT

# Enable debug mode to see what's happening, run DEBUG=true ./start.sh
[ "${DEBUG:-}" = "true" ] && set -x

echo -e "Starting the Airweave Engine..."

# Create .env if it doesn't exist
[ -f .env ] || {
  echo -e "Creating .env from .env.example..."
  cp .env.example .env
  echo -e "✅ .env created"
}

# Update ENCRYPTION_KEY
NEW_KEY=$(openssl rand -base64 32)
grep -v "^ENCRYPTION_KEY=" .env > .env.tmp || true
echo -e "ENCRYPTION_KEY=\"$NEW_KEY\"" >> .env.tmp
mv .env.tmp .env
echo -e "🔐 ENCRYPTION_KEY set."

# Ask for OpenAI API key if not already present or empty
OPENAI_KEY_LINE=$(grep "^OPENAI_API_KEY=" .env || true)
OPENAI_KEY_VALUE="${OPENAI_KEY_LINE#*=}"

if [[ -z "$OPENAI_KEY_VALUE" ]]; then
  echo -e "\nOpenAI API key is required for files and natural language search."
  echo -e "📝 You can add it later in your .env file manually."
  read -p "Would you like to add your OPENAI_API_KEY now? (y/N): " ADD_KEY

  if [[ "$ADD_KEY" =~ ^[Yy]$ ]]; then
    read -p "Enter your OpenAI API key: " OPENAI_KEY
    grep -v "^OPENAI_API_KEY=" .env > .env.tmp || true
    echo -e "OPENAI_API_KEY=\"$OPENAI_KEY\"" >> .env.tmp
    mv .env.tmp .env
    echo -e "✅ OPENAI_API_KEY added."
  fi
else
  echo -e "🔑 OPENAI_API_KEY is already set."
fi

# Determine docker compose command
COMPOSE_CMD="docker compose"
docker compose version >/dev/null 2>&1 || {
  COMPOSE_CMD="docker-compose"
  docker-compose --version >/dev/null 2>&1 || {
    echo -e "❌ Docker Compose not found."
    exit 1
  }
}

echo -e "\n🚀 Starting services with: $COMPOSE_CMD"
$COMPOSE_CMD up -d

echo -e "\nServices started!"
echo -e "Frontend is running at: http://localhost:8080"
