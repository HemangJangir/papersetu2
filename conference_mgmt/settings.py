import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-please-change-this-key')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Get allowed hosts from environment variable, with fallback for development
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = allowed_hosts_env.split(',')
else:
    # Default hosts for development
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'papersetu2.onrender.com', '*.onrender.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'accounts',
    'conference',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conference_mgmt.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'conference_mgmt.wsgi.application'

# Database configuration
if os.environ.get('DATABASE_URL'):
    # Production database (PostgreSQL on Render)
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    # Development database (SQLite)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Add whitenoise middleware for static files in production
if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

# Custom authentication backend for email/username login
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'papersetu@gmail.com'  # <-- Replace with your Gmail address
EMAIL_HOST_PASSWORD = 'unhh ovcr cqri wxwr'  # <-- Replace with your Gmail app password
DEFAULT_FROM_EMAIL = 'papersetu@gmail.com'

# SSL Certificate verification settings - disable certificate verification for development
import ssl
EMAIL_SSL_CONTEXT = ssl.create_default_context()
EMAIL_SSL_CONTEXT.check_hostname = False
EMAIL_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Alternative: Use console backend for development/testing
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For development: Use console backend to avoid SSL issues
# Uncomment the line below to see emails in console instead of sending them
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For production: Use SMTP with proper SSL handling
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

LOGIN_REDIRECT_URL = '/' 

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_...')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_...')
STRIPE_PAYMENT_AMOUNT = 50000  # Amount in paise (₹500 = 50000 paise)
STRIPE_CURRENCY = 'inr' 

SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'https://papersetu2.onrender.com') 