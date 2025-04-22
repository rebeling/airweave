#!/bin/sh
set -e

# Determine if auth should be enabled
# Priority: 1. ENABLE_AUTH env var 2. If AUTH0 vars present 3. Default off
if [ "${ENABLE_AUTH}" = "true" ]; then
  AUTH_ENABLED=true
elif [ -n "$AUTH0_DOMAIN" ] && [ -n "$AUTH0_CLIENT_ID" ] && [ -n "$AUTH0_AUDIENCE" ]; then
  AUTH_ENABLED=true
  echo "Auth enabled because Auth0 credentials are provided"
else
  AUTH_ENABLED=false
  echo "Auth disabled (no credentials or ENABLE_AUTH not set to true)"
fi

# Create runtime config with environment variables
cat > /app/dist/config.js << EOF
window.ENV = {
  API_URL: "${API_URL:-/api}",
  AUTH_ENABLED: ${AUTH_ENABLED},
  AUTH0_DOMAIN: "${AUTH0_DOMAIN:-}",
  AUTH0_CLIENT_ID: "${AUTH0_CLIENT_ID:-}",
  AUTH0_AUDIENCE: "${AUTH0_AUDIENCE:-}"
};
EOF

echo "Configuration generated successfully"

# Run the command
exec serve -s /app/dist -l 8080 --no-clipboard --no-port-switching
