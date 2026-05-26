import glob
import json
import logging
import shutil
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

# Extensões temporárias de download — arquivo ainda sendo gravado
_TEMP_EXTENSIONS = {'.crdownload', '.part', '.download', '.tmp', '.partial', '.opdownload'}

# Registro global: caso_pk -> (Observer, watch_folder_str)
# Funciona para runserver (processo único). Com múltiplos workers gunicorn
# seria necessário um backend externo (Redis, DB) para coordenar estado.
_WATCHERS: dict = {}
_LOCK = threading.Lock()


class _DownloadEventHandler(FileSystemEventHandler):
    def __init__(self, caso_pk: int, caso_path: str, analista_pk: int):
        self._caso_pk = caso_pk
        self._caso_path = Path(caso_path)
        self._analista_pk = analista_pk
        self._processing: set = set()

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() in _TEMP_EXTENSIONS:
            return
        self._dispatch(path)

    def on_moved(self, event):
        if event.is_directory:
            return
        src = Path(event.src_path)
        dest = Path(event.dest_path)
        if dest.suffix.lower() in _TEMP_EXTENSIONS:
            return
        # .crdownload → arquivo final: download concluído
        if src.suffix.lower() in _TEMP_EXTENSIONS:
            self._dispatch(dest)

    def _dispatch(self, path: Path):
        key = str(path)
        with _LOCK:
            if key in self._processing:
                return
            self._processing.add(key)
        threading.Thread(target=self._process, args=(path,), daemon=True).start()

    def _process(self, path: Path):
        try:
            if not self._wait_stable(path):
                return
            if not path.exists():
                return
            self._save_to_case(path)
        finally:
            with _LOCK:
                self._processing.discard(str(path))

    def _wait_stable(self, path: Path, checks: int = 3, interval: float = 1.5) -> bool:
        last_size = -1
        stable = 0
        for _ in range(20):
            try:
                size = path.stat().st_size
            except OSError:
                time.sleep(interval)
                continue
            if size > 0 and size == last_size:
                stable += 1
                if stable >= checks:
                    return True
            else:
                stable = 0
                last_size = size
            time.sleep(interval)
        return False

    def _save_to_case(self, src: Path):
        from django.db import connection
        from django.utils import timezone

        from core.models import Analista, Caso, Evidencia
        from core.services.audit_logger import AuditLogger
        from core.services.hash_service import HashService

        try:
            caso = Caso.objects.get(pk=self._caso_pk)
            analista = Analista.objects.get(pk=self._analista_pk)

            output_dir = self._caso_path / 'downloads'
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            dest = output_dir / f'{timestamp}_{src.name}'
            shutil.copy2(src, dest)

            hash_sha256 = HashService.hash_file(dest)
            detected_at = timezone.now().isoformat()

            origem = self._detect_origin(src.name) or 'desconhecida'
            metadata = {
                'original_name': src.name,
                'filename': dest.name,
                'size_bytes': dest.stat().st_size,
                'detected_at_utc': detected_at,
                'source_path': str(src),
                'origem': origem,
            }

            dest.with_suffix(dest.suffix + '.json').write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

            Evidencia.objects.create(
                caso=caso,
                tipo=Evidencia.Tipo.DOWNLOAD,
                hash_sha256=hash_sha256,
                path_arquivo=str(dest),
                metadados_json=metadata,
            )
            AuditLogger.log(caso, analista, 'DOWNLOAD_DETECTADO', {
                'filename': src.name,
                'hash_sha256': hash_sha256,
                'size_bytes': metadata['size_bytes'],
                'origem': origem,
            })
        except Exception:
            logger.exception('Erro ao registrar download detectado: %s', src)
        finally:
            connection.close()

    @staticmethod
    def _detect_origin(filename: str) -> str | None:
        """Tenta encontrar a URL de origem no histórico do Chrome (melhor esforço)."""
        try:
            patterns = [
                str(Path.home() / '.config/google-chrome/*/History'),
                str(Path.home() / '.config/chromium/*/History'),
                str(Path.home() / 'snap/chromium/*/History'),
            ]
            db_paths = []
            for pattern in patterns:
                db_paths.extend(glob.glob(pattern))

            for db_path in db_paths:
                with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    shutil.copy2(db_path, tmp_path)
                    conn = sqlite3.connect(tmp_path)
                    row = conn.execute(
                        'SELECT tab_url FROM downloads '
                        'WHERE target_path LIKE ? '
                        'ORDER BY start_time DESC LIMIT 1',
                        (f'%{filename}',),
                    ).fetchone()
                    conn.close()
                    if row and row[0]:
                        return row[0]
                except Exception:
                    pass
                finally:
                    Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        return None


class DownloadWatcherService:
    @staticmethod
    def start(caso_pk: int, watch_folder: str, caso_path: str, analista_pk: int) -> None:
        with _LOCK:
            if caso_pk in _WATCHERS:
                return

        watch_path = Path(watch_folder).expanduser()
        watch_path.mkdir(parents=True, exist_ok=True)

        handler = _DownloadEventHandler(caso_pk, caso_path, analista_pk)
        observer = Observer()
        observer.schedule(handler, str(watch_path), recursive=False)
        observer.start()

        with _LOCK:
            _WATCHERS[caso_pk] = (observer, str(watch_path))

    @staticmethod
    def stop(caso_pk: int) -> None:
        with _LOCK:
            entry = _WATCHERS.pop(caso_pk, None)
        if entry:
            observer, _ = entry
            observer.stop()
            observer.join(timeout=5)

    @staticmethod
    def is_active(caso_pk: int) -> bool:
        with _LOCK:
            return caso_pk in _WATCHERS

    @staticmethod
    def watch_folder(caso_pk: int) -> str | None:
        with _LOCK:
            entry = _WATCHERS.get(caso_pk)
            return entry[1] if entry else None
