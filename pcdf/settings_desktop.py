"""
Desktop settings — SQLite + WhiteNoise + sem PostgreSQL/docker.
Usado pelo main.py e pelo PyInstaller (DJANGO_SETTINGS_MODULE=pcdf.settings_desktop).
NÃO herda de settings.py para evitar dependência do python-decouple/.env.
"""
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Dados persistentes do usuário (sobrevivem a updates do app) ────────────
DATA_DIR = Path.home() / 'EDIFRAUDS'
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Chave secreta: gerada uma vez e persistida ─────────────────────────────
_SECRET_FILE = DATA_DIR / '.secret_key'
if _SECRET_FILE.exists():
    SECRET_KEY = _SECRET_FILE.read_text(encoding='utf-8').strip()
else:
    SECRET_KEY = 'edifrauds-' + secrets.token_urlsafe(50)
    _SECRET_FILE.write_text(SECRET_KEY, encoding='utf-8')

DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Permite requests vindos do navegador local sem verificação de origin
CSRF_TRUSTED_ORIGINS = ['http://localhost:8765', 'http://127.0.0.1:8765']

# Em modo desktop local não é necessário segurança via HTTPS
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ── Apps ───────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

# WhiteNoise serve os estáticos diretamente pelo Django (sem nginx)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'pcdf.urls_desktop'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'pcdf.wsgi.application'

# ── SQLite — sem servidor de banco externo ─────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATA_DIR / 'edifrauds.db',
    }
}

# ── Validação de senhas ────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Localização ───────────────────────────────────────────────────────────
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ── Arquivos estáticos — WhiteNoise serve do staticfiles coletado ──────────
STATIC_URL = '/static/'

# Dentro do bundle PyInstaller os estáticos ficam em _MEIPASS/staticfiles
if hasattr(sys, '_MEIPASS'):
    STATIC_ROOT = Path(sys._MEIPASS) / 'staticfiles'
else:
    STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_MAX_AGE = 86400

# ── Mídia (uploads, logos, evidências) ────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = DATA_DIR / 'media'

# ── Pastas de casos e downloads ───────────────────────────────────────────
CASES_ROOT = DATA_DIR / 'casos'
WATCH_FOLDER = DATA_DIR / 'watch_downloads'

for _d in [MEDIA_ROOT, CASES_ROOT, WATCH_FOLDER]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Auth ───────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.Analista'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'casos'
LOGOUT_REDIRECT_URL = 'login'

# ── Log em arquivo na pasta de dados ─────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': str(DATA_DIR / 'edifrauds.log'),
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'WARNING',
    },
}
