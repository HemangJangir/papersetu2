#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Collect static files including admin
python manage.py collectstatic --no-input --clear

# Run migrations
python manage.py migrate

# Setup admin interface
python manage.py setup_admin_interface

# Create superuser if it doesn't exist (optional)
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell 