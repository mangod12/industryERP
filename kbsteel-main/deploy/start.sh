#!/usr/bin/env bash
# =============================================================================
# KumarBrothers Steel ERP — Production Startup Script
# =============================================================================
# Usage:
#   chmod +x deploy/start.sh
#   ./deploy/start.sh
#
# Prerequisites:
#   1. Create .env file from .env.example and fill in production values
#   2. Install dependencies: pip install -r requirements.txt
#   3. Set up Nginx with deploy/nginx.conf
#   4. Set up SSL: sudo certbot --nginx -d kumarbrothersbksc.in
# =============================================================================

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "[deploy] Loaded .env file"
else
    echo "[deploy] ERROR: .env file not found! Copy .env.example to .env first."
    exit 1
fi

# Verify required env vars
if [ -z "$DATABASE_URL" ]; then
    echo "[deploy] ERROR: DATABASE_URL is not set in .env"
    exit 1
fi

if [ -z "$KUMAR_SECRET_KEY" ] || [ "$KUMAR_SECRET_KEY" = "GENERATE_A_64_CHAR_RANDOM_SECRET_HERE" ]; then
    echo "[deploy] ERROR: KUMAR_SECRET_KEY must be set to a real secret!"
    echo "  Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    exit 1
fi

# Set production mode
export ENVIRONMENT=production

echo "[deploy] Starting KumarBrothers Steel ERP..."
echo "[deploy] Database: ...@$(echo $DATABASE_URL | cut -d'@' -f2)"
echo "[deploy] Workers: 4"

# Start with Gunicorn + Uvicorn workers for production performance
# - 4 workers (adjust based on CPU cores: 2 * cores + 1)
# - Bind to localhost only (Nginx handles external traffic)
# - Access log to file
exec gunicorn backend_core.app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/kbsteel/access.log \
    --error-logfile /var/log/kbsteel/error.log \
    --timeout 120 \
    --graceful-timeout 30
