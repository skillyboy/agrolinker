import os
from pathlib import Path
from dotenv import load_dotenv
from os import getenv
# import dj_database_url
from datetime import timedelta  
# from pydantic_settings import BaseSettings
from typing import List
import os
# from agro_linker.models.user import *
# from .user import *

load_dotenv()
# Define the base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load Environment Variables
load_dotenv(BASE_DIR / ".env")

# CORS Origins
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",  # React frontend
    "http://localhost:8000",  # Django admin
]
    

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = getenv("SECRET_KEY")

# settings.py
# DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

DEBUG = True

YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "http://127.0.0.1:8000")


# For production with domains, use:
ALLOWED_HOSTS = ['*']  # Not recommended for production

API_V1_STR: str = "/v1"
PROJECT_NAME: str = "AgroLinker"


ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30









# Stripe settings

STRIPE_PUBLIC_KEY = getenv("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY  = getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET=getenv("STRIPE_WEBHOOK_SECRET")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    # 'afriapp',
    'agro_linker',

    'ninja',
    'corsheaders',
    'django_redis',
    'django.contrib.postgres',  # For PostgreSQL specific features
]


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PASSWORD": "your-redis-password",  # Add Redis password
            "SOCKET_CONNECT_TIMEOUT": 5,  # seconds
            "SOCKET_TIMEOUT": 5,  # seconds
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 1000,
        },
        "KEY_PREFIX": "agro_linker",  # Prevent key collisions
        "TIMEOUT": 300,  # 5 minutes default timeout
    }
}

# Add a local memory fallback cache
CACHES["backup"] = {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "fallback",
}

NINJA_PAGINATION_CLASS = 'ninja.pagination.LimitOffsetPagination'
NINJA_LIMIT_OFFSET_PAGINATION_DEFAULT_LIMIT = 50




MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# The URL to use when referring to static files (where they will be served from)

# Additional directories to look for static files (if you have a 'static' directory in your apps)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR,'agro_linker', 'static'),  # This is your local static directory
]

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'uploads'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # or leave it as []
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

WSGI_APPLICATION = 'project.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('POSTGRES_DB', 'postgres'),
#         'USER': os.getenv('POSTGRES_USER', 'postgres'),
#         'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'skilly1234'),
#         'HOST': os.getenv('DB_HOST', 'db'), 
#         'PORT': os.getenv('DB_PORT', '5432'),
#     }
# }

# DATABASES = {
#     'default': dj_database_url.parse(
#         # 'postgresql://africandb_3g6p_user:TGvIOVHFpRqR6eZUlsuHUouM6tHOmq48@dpg-csfdi5hu0jms73ffcm90-a.oregon-postgres.render.com/africandb_3g6p'
#         "postgresql://afrigold_owner:npg_ouZ8jIFmsUB6@ep-dry-pond-a51vp14m-pooler.us-east-2.aws.neon.tech/afrigold?sslmode=require"
#     )
# }

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators




# CORS settings
CORS_ALLOW_ALL_ORIGINS = True

# Development-specific settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Security settings
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS=on
# FORCE_SSL=1
# SECURE_SSL_REDIRECT=1
SITE_ID = 1

# # Custom user model
# AUTH_USER_MODEL = 'agro_linker.User'

# Rest Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

SIMPLE_JWT = {
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

# api = NinjaAPI(
#     title="Agro Linker API",
#     version="1.0.0",
#     description="API for the Agro Linker platform",
#     docs_url="/docs",
#     openapi_url="/openapi.json",
#     urls_namespace="agro_linker_api"
# )