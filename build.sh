#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "INFO: Starting build process..."

# Install Python dependencies
echo "INFO: Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# Add any other build steps here if needed in the future
# For example, if you were using Flask-Migrate for database migrations:
# echo "INFO: Running database migrations..."
# flask db upgrade

# If you had frontend assets to build (not currently the case):
# echo "INFO: Building frontend assets..."
# npm install && npm run build

echo "INFO: Build process completed."