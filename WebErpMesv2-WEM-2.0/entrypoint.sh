#!/bin/sh

# Stop the script in case of an error
set -e

echo "🏭 Starting Kumar Brothers Steel ERP..."

# Grant the necessary permissions
chown -R www-data:www-data /app/storage /app/bootstrap/cache
chmod -R 775 /app/storage /app/bootstrap/cache

# Check if .env exists, otherwise copy the template
if [ ! -f ".env" ]; then
    echo "📌 .env file not found! Copying .env.example..."
    cp .env.example .env
else
    echo "✅ .env file already exists. Keeping current settings."
fi

echo "🔍 Checking environment variables..."
echo "🔍 DB_HOST: $DB_HOST"
echo "🔍 DB_PORT: $DB_PORT"
echo "🔍 DB_DATABASE: $DB_DATABASE"
echo "🔍 DB_USERNAME: $DB_USERNAME"

# Wait for the database to be available
timeout=30
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  echo "⏳ Waiting for database ($DB_HOST:$DB_PORT)..."
  sleep 5
  timeout=$((timeout - 5))
  if [ "$timeout" -le 0 ]; then
    echo "❌ Database is not available after 30 seconds. Exiting."
    exit 1
  fi
done


# Install dependencies if necessary
if [ ! -f "vendor/autoload.php" ]; then
    echo "📦 Installing Composer dependencies..."
    export COMPOSER_MEMORY_LIMIT="-1"
    export COMPOSER_PROCESS_TIMEOUT="0"
    export COMPOSER_ALLOW_SUPERUSER="1"
    composer install --no-interaction --prefer-dist --optimize-autoloader --no-progress
fi

if [ ! -d "node_modules" ] || [ ! -f "public/build/manifest.json" ]; then
    echo "📦 Installing NPM dependencies..."
    npm install
    if node -e "const pkg=require('./package.json'); process.exit(pkg?.scripts?.build ? 0 : 1)"; then
        npm run build
    else
        echo "ℹ️ package.json has no build script; skipping frontend build."
    fi
fi

# Generate application key if needed
if [ -z "$(grep APP_KEY .env | cut -d '=' -f2)" ]; then
    echo "🔑 Generating application key..."
    php artisan key:generate
fi

# Run migrations and seeders if needed
echo "📜 Waiting 10 seconds for MySQL to be ready..."
sleep 10
echo "📜 Running migrations..."
echo "✅ Kumar Brothers Steel ERP initializing..."
php artisan migrate --force

# Seeding the database
echo "🌱 Seeding the database...(PermissionTableSeeder / CreateAdminUserSeeder)"
php artisan db:seed --class=PermissionTableSeeder
php artisan db:seed --class=CreateAdminUserSeeder

echo "✅ Admin user created successfully!"

# Clear and cache the configuration
echo "⚡ Optimizing Laravel..."
php artisan config:clear
php artisan cache:clear
php artisan config:cache
if php artisan route:cache; then
    echo "Routes cached successfully."
else
    echo "Route cache failed; continuing without cached routes."
    php artisan route:clear
fi
php artisan view:cache
echo "⚙️ Optimizing Composer autoload..."
composer dump-autoload --optimize
echo "📌 Kumar Brothers Steel ERP is ready!"
echo "⚡ Launching Kumar Brothers Steel ERP server..."
exec php artisan serve --host=0.0.0.0 --port=8000
echo "✅ Kumar Brothers Steel ERP is now running!"