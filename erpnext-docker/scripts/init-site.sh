#!/bin/bash
# Kumar Brothers Steel ERP - Site Setup Script
# This script initializes the ERPNext site with steel industry configuration

set -e

SITE_NAME="${SITE_NAME:-frontend}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-kumar_root_2026}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-KumarAdmin@2026}"

echo "==================================================="
echo "Kumar Brothers Steel ERP - Site Initialization"
echo "==================================================="
echo ""

cd /home/frappe/frappe-bench

# Wait for MariaDB to be ready
echo "[1/7] Waiting for MariaDB..."
sleep 10
until mysql -h mariadb -u root -p"$DB_ROOT_PASSWORD" -e "SELECT 1" > /dev/null 2>&1; do
    echo "MariaDB not ready, waiting..."
    sleep 5
done
echo "✓ MariaDB is ready"

# Configure bench
echo "[2/7] Configuring bench..."
bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379
bench set-config -g serve_default_site true
echo "✓ Bench configured"

# Check if site already exists
if [ -d "sites/$SITE_NAME" ]; then
    echo "[3/7] Site '$SITE_NAME' already exists, skipping creation"
else
    echo "[3/7] Creating new site: $SITE_NAME..."
    bench new-site "$SITE_NAME" \
        --db-root-password "$DB_ROOT_PASSWORD" \
        --admin-password "$ADMIN_PASSWORD" \
        --install-app erpnext \
        --set-default
    echo "✓ Site created successfully"
fi

# Set as default site
echo "[4/7] Setting default site..."
bench use "$SITE_NAME"
echo "$SITE_NAME" > sites/currentsite.txt
echo "✓ Default site set to $SITE_NAME"

# Enable scheduler
echo "[5/7] Enabling scheduler..."
bench --site "$SITE_NAME" enable-scheduler
echo "✓ Scheduler enabled"

# Build assets
echo "[6/7] Building assets..."
bench build --force
echo "✓ Assets built"

# Run migrations
echo "[7/7] Running migrations..."
bench --site "$SITE_NAME" migrate
echo "✓ Migrations complete"

echo ""
echo "==================================================="
echo "✓ Site initialization complete!"
echo "==================================================="
echo ""
echo "Access ERPNext at: http://localhost:8080"
echo "Username: Administrator"
echo "Password: $ADMIN_PASSWORD"
echo ""
