"""
build_exe.py — Empacota o EDIFRAUDS como executável standalone.

Uso:
    python build_exe.py

O que faz:
    1. Instala dependências de requirements_desktop.txt
    2. Baixa e instala o Playwright Chromium
    3. Roda collectstatic do Django
    4. Executa PyInstaller com edifrauds.spec
    5. Compacta o resultado em EDIFRAUDS_<plataforma>.zip

Resultado: dist/EDIFRAUDS/ — pasta com o executável e tudo incluso.
           EDIFRAUDS_win64.zip (ou linux64) — pronto para enviar.

IMPORTANTE: Execute este script na plataforma alvo (Windows para gerar .exe).
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / 'dist' / 'EDIFRAUDS'


def run(cmd: list[str], **kwargs) -> None:
    print(f'\n>>> {" ".join(str(c) for c in cmd)}')
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f'\nERRO: comando falhou com código {result.returncode}')
        sys.exit(result.returncode)


def step(msg: str) -> None:
    print(f'\n{"─" * 60}')
    print(f'  {msg}')
    print('─' * 60)


def main() -> None:
    step('1/5 — Instalando dependências desktop')
    run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements_desktop.txt', '--upgrade'])

    step('2/5 — Instalando Playwright Chromium (offline bundle)')
    run([sys.executable, '-m', 'playwright', 'install', 'chromium'])

    step('3/5 — Coletando arquivos estáticos (collectstatic)')
    env = os.environ.copy()
    env['DJANGO_SETTINGS_MODULE'] = 'pcdf.settings_desktop'

    # collectstatic precisa de STATIC_ROOT apontando para o projeto (não _MEIPASS)
    # Forçamos a variável para o caminho local de build
    static_root = str(ROOT / 'staticfiles')
    # Sobrescreve temporariamente via env var que o settings_desktop lê via sys._MEIPASS check
    # Como não estamos dentro do bundle (_MEIPASS não existe), ele usará BASE_DIR/staticfiles
    run(
        [sys.executable, 'manage.py', 'collectstatic', '--noinput', '--clear'],
        env=env,
        cwd=ROOT,
    )

    step('4/5 — Empacotando com PyInstaller')
    # Limpa build anterior
    for d in [ROOT / 'build', ROOT / 'dist']:
        if d.exists():
            shutil.rmtree(d)
            print(f'  Removido: {d}')

    run(
        [sys.executable, '-m', 'PyInstaller', 'edifrauds.spec', '--noconfirm'],
        cwd=ROOT,
        env=env,
    )

    if not DIST.exists():
        print(f'\nERRO: PyInstaller não gerou {DIST}')
        sys.exit(1)

    step('5/5 — Compactando para envio')
    plat = 'win64' if platform.system() == 'Windows' else 'linux64'
    zip_name = ROOT / f'EDIFRAUDS_{plat}'
    shutil.make_archive(str(zip_name), 'zip', ROOT / 'dist', 'EDIFRAUDS')
    zip_file = Path(str(zip_name) + '.zip')

    print(f'\n{"=" * 60}')
    print('  BUILD CONCLUÍDO COM SUCESSO!')
    print(f'  Pasta:     {DIST}')
    print(f'  ZIP:       {zip_file}  ({zip_file.stat().st_size // 1_048_576} MB)')
    print()
    print('  Para testar localmente:')
    if platform.system() == 'Windows':
        print(f'    {DIST}\\EDIFRAUDS.exe')
    else:
        print(f'    {DIST}/EDIFRAUDS')
    print()
    print('  Para enviar ao delegado:')
    print(f'    Envie o arquivo: {zip_file.name}')
    print('    Instrução: extraia a pasta e execute EDIFRAUDS.exe')
    print('=' * 60)


if __name__ == '__main__':
    main()
