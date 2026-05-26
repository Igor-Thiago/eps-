# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — EDIFRAUDS desktop EXE.

O que vai no bundle:
  - templates/         → HTML (não são código Python)
  - core/migrations/   → descobertos pelo Django via filesystem, não por import
  - core/management/   → idem
  - staticfiles/       → gerado por collectstatic antes de rodar este spec
  - playwright_browsers/ → Chromium headless (offline)

Gerado pelo build_exe.py — não execute pyinstaller diretamente.
"""
import os
import sys
from pathlib import Path

block_cipher = None

# Garante que a análise do PyInstaller use as configurações desktop.
# Sem isso, o hook do Django pode cair em pcdf.settings.py e exigir
# dependências exclusivas do modo Docker/servidor.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pcdf.settings_desktop')

ROOT = Path(SPECPATH)  # noqa: F821 — injetado pelo PyInstaller


# ── Localiza o Chromium instalado pelo Playwright ─────────────────────────
def _find_playwright_browsers_root() -> Path | None:
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'ms-playwright'
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Caches' / 'ms-playwright'
    else:
        base = Path.home() / '.cache' / 'ms-playwright'

    env_override = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
    if env_override and env_override != '0':
        base = Path(env_override)

    return base if base.exists() else None


playwright_browsers_root = _find_playwright_browsers_root()

# ── Dados a incluir (somente arquivos não-Python ou descobertos via fs) ────
datas = [
    # Templates HTML
    (str(ROOT / 'templates'), 'templates'),
    # Migrations: Django as descobre via listagem do filesystem
    (str(ROOT / 'core' / 'migrations'), 'core/migrations'),
    # Management commands: também descobertos via filesystem
    (str(ROOT / 'core' / 'management'), 'core/management'),
    # Estáticos coletados (gerado por collectstatic antes do build)
    (str(ROOT / 'staticfiles'), 'staticfiles'),
]

if playwright_browsers_root:
    print(f'[spec] Incluindo navegadores do Playwright: {playwright_browsers_root}')
    datas.append((str(playwright_browsers_root), 'playwright_browsers'))
else:
    print('[spec] AVISO: diret?rio de navegadores do Playwright n?o encontrado. '
          'Execute: python -m playwright install chromium')

# ── Hidden imports — Django usa importação dinâmica, PyInstaller não detecta
hidden_imports = [
    # Django core
    'django.contrib.admin',
    'django.contrib.admin.apps',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sessions.backends.db',
    'django.contrib.messages',
    'django.contrib.messages.storage.fallback',
    'django.contrib.staticfiles',
    'django.middleware.security',
    'django.template.defaulttags',
    'django.template.defaultfilters',
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
    'django.db.backends.sqlite3',
    # App core
    'core',
    'core.models',
    'core.views',
    'core.forms',
    'core.urls',
    'core.admin',
    'core.apps',
    'core.services',
    'core.services.audit_logger',
    'core.services.case_folder_service',
    'core.services.certidao_service',
    'core.services.crypto_service',
    'core.services.download_watcher_service',
    'core.services.forensic_copy_service',
    'core.services.forensic_report_service',
    'core.services.hash_service',
    'core.services.integrity_report_service',
    'core.services.metadata_service',
    'core.services.screen_recording_service',
    'core.services.screenshot_service',
    'core.services.site_preserver',
    'core.management.commands.criar_admin',
    # Settings e URLs desktop
    'pcdf.settings_desktop',
    'pcdf.urls_desktop',
    # WhiteNoise
    'whitenoise',
    'whitenoise.middleware',
    'whitenoise.storage',
    'whitenoise.responders',
    'whitenoise.compress',
    # Playwright
    'playwright',
    'playwright.sync_api',
    'playwright._impl._sync_base',
    'playwright._impl._browser',
    'playwright._impl._browser_context',
    'playwright._impl._page',
    'playwright._impl._driver',
    # Criptografia
    'cryptography',
    'cryptography.hazmat.primitives.ciphers.aead',
    'cryptography.hazmat.backends',
    # Relatórios
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.platypus',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.lib.styles',
    'docx',
    'docx.oxml',
    'docx.oxml.ns',
    'docx.shared',
    'docx.enum.text',
    # Imagens e utilidades
    'PIL',
    'PIL.Image',
    'pydantic',
    'dns',
    'dns.resolver',
    'httpx',
    'watchdog',
    'watchdog.observers',
    'watchdog.events',
]

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Não usados no modo desktop
        'psycopg2',
        'psycopg2-binary',
        'decouple',
        'python-decouple',
        # Ferramentas de teste (não vão no EXE)
        'pytest',
        'pytest_django',
        'pytest_cov',
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EDIFRAUDS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    # console=True mantém janela do terminal visível (mostra status e logs)
    console=True,
    icon=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EDIFRAUDS',
)
