import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-only-change-in-production')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[],
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'loja',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'loja.middleware.LimiteUploadMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'loja.context_processors.carrinho_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


def _conectar_postgres(url, timeout):
    import psycopg2

    conexao = psycopg2.connect(url, connect_timeout=timeout)
    conexao.close()


_rodando_testes = len(sys.argv) > 1 and sys.argv[1] == 'test'
_database_url = '' if _rodando_testes else (env('DATABASE_URL', default='') or '')
if _database_url:
    # Postgres online. Sem ele o Render free gravava num SQLite que some no restart.
    DATABASES = {'default': env.db('DATABASE_URL')}
    opcoes = DATABASES['default'].setdefault('OPTIONS', {})
    opcoes.setdefault('connect_timeout', 10)
    if 'supabase.com' in _database_url and 'sslmode' not in opcoes:
        opcoes['sslmode'] = 'require'
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_VERSION = '20261008remover'

STORAGES = {
    'default': {
        'BACKEND': 'loja.storage.SafeFileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# Em desenvolvimento o WhiteNoise lê a pasta static/ direto, sem collectstatic.
if DEBUG:
    WHITENOISE_USE_FINDERS = True

CLOUDINARY_URL = env('CLOUDINARY_URL', default='')
SUPABASE_URL = env('SUPABASE_URL', default='')
SUPABASE_SERVICE_ROLE_KEY = env('SUPABASE_SERVICE_ROLE_KEY', default='')
SUPABASE_BUCKET = env('SUPABASE_BUCKET', default='midia')
# Bunny Stream → Library → Security → "Embed view token authentication"
BUNNY_STREAM_TOKEN_KEY = env('BUNNY_STREAM_TOKEN_KEY', default='')
USAR_SUPABASE = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY) and not _rodando_testes
if USAR_SUPABASE:
    STORAGES['default'] = {
        'BACKEND': 'loja.storage.SupabaseStorage',
    }
elif CLOUDINARY_URL and not _rodando_testes:
    STORAGES['default'] = {
        'BACKEND': 'loja.storage.CloudinaryAutoStorage',
    }

# YouTube embeds exigem Referer; o default do Django (same-origin) suprime
# e causa Error 153 no player embutido.
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Acima de 20 MB o arquivo vai para disco temporário, sem ocupar a memória inteira.
FILE_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
# No ar, o plano gratuito da nuvem recusa arquivo maior que 50 MB.
# Acima disso o servidor free cai e a página perde o CSS.
DATA_UPLOAD_MAX_MEMORY_SIZE = (8 * 1024 if DEBUG else 52) * 1024 * 1024

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

MERCADOPAGO_ACCESS_TOKEN = env('MERCADOPAGO_ACCESS_TOKEN', default='')
MERCADOPAGO_PUBLIC_KEY = env('MERCADOPAGO_PUBLIC_KEY', default='')
MERCADOPAGO_WEBHOOK_SECRET = env('MERCADOPAGO_WEBHOOK_SECRET', default='')
# True só no sandbox. Em produção (DEBUG=False) o checkout cobra de verdade.
MERCADOPAGO_SANDBOX = env.bool('MERCADOPAGO_SANDBOX', default=DEBUG)
SITE_URL = env('SITE_URL', default='http://localhost:8000')

EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env(
    'DEFAULT_FROM_EMAIL',
    default='Vinil & Página <noreply@localhost>',
)

if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
OPENAI_MODEL = env('OPENAI_MODEL', default='gpt-4o-mini')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'loja': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
