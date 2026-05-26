"""
EDIFRAUDS — ponto de entrada para o executável desktop.

Fluxo:
  1. Configura variáveis de ambiente (settings, Playwright)
  2. Inicia o servidor Django em uma thread daemon
  3. Aguarda o servidor aceitar conexões (até 30s)
  4. Abre o navegador padrão do usuário em http://127.0.0.1:8765
  5. Mantém o processo vivo até o usuário fechar a janela do terminal

Para criar o EXE use: python build_exe.py
"""
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT = 8765
HOST = '127.0.0.1'


def _resource(relative: str) -> Path:
    """Resolve caminho dentro do bundle PyInstaller ou da árvore de código."""
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    return base / relative


def _wait_for_server(timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            socket.create_connection((HOST, PORT), timeout=1).close()
            return True
        except OSError:
            time.sleep(0.3)
    return False


def _run_django() -> None:
    import django
    from django.core.management import call_command

    django.setup()
    # Aplica migrations (cria banco SQLite na primeira execução)
    call_command('migrate', '--run-syncdb', verbosity=0)
    call_command(
        'runserver',
        f'{HOST}:{PORT}',
        '--noreload',
        '--nothreading',
    )


def main() -> None:
    # Adiciona raiz do bundle ao sys.path (necessário para PyInstaller)
    bundle_root = str(_resource('.'))
    if bundle_root not in sys.path:
        sys.path.insert(0, bundle_root)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pcdf.settings_desktop')

    # Aponta Playwright para o Chromium embutido no bundle (se presente)
    chromium_bundle = _resource('playwright_browsers')
    if chromium_bundle.exists():
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(chromium_bundle)

    print('=' * 55)
    print('  EDIFRAUDS — Sistema de Preservação de Vestígios Digitais')
    print('  CORF / PCDF')
    print('=' * 55)
    print(f'\n  Iniciando servidor em http://{HOST}:{PORT} ...')
    print('  Dados salvos em:', Path.home() / 'EDIFRAUDS')
    print('\n  NÃO feche esta janela enquanto estiver usando o sistema.')
    print('  Para encerrar: feche o navegador e pressione Ctrl+C aqui.\n')

    thread = threading.Thread(target=_run_django, daemon=True)
    thread.start()

    if not _wait_for_server():
        print('\n  ERRO: O servidor não iniciou em 30 segundos.')
        print('  Verifique o log em ~/EDIFRAUDS/edifrauds.log')
        input('\n  Pressione Enter para sair...')
        sys.exit(1)

    webbrowser.open(f'http://{HOST}:{PORT}')

    try:
        thread.join()
    except KeyboardInterrupt:
        print('\n  EDIFRAUDS encerrado.')


if __name__ == '__main__':
    main()
