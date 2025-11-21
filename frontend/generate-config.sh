#!/bin/sh
# Generate runtime configuration from environment variables

cat <<EOF > /usr/share/nginx/html/config.js
window.__RUNTIME_CONFIG__ = {
  VITE_API_URL: '${VITE_API_URL:-http://localhost:8000}'
};
EOF

echo "Generated config.js with VITE_API_URL=${VITE_API_URL:-http://localhost:8000}"
