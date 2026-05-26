import json
import re
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone

from .hash_service import HashService


class ScreenRecordingError(Exception):
    pass


@dataclass(frozen=True)
class ScreenRecordingResult:
    path: Path
    hash_sha256: str
    filename: str
    size_bytes: int
    recorded_at_utc: str
    metadata: dict


class ScreenRecordingService:
    ALLOWED_EXTENSIONS = {'.webm', '.mp4'}

    def save_recording(self, caso, uploaded_file, metadata: dict | None = None) -> ScreenRecordingResult:
        if not uploaded_file:
            raise ScreenRecordingError('Nenhum video de gravacao foi enviado.')

        metadata = metadata or {}
        extension = self._extension(uploaded_file.name)
        recording_id = self._safe_identifier(metadata.get('recording_id') or 'gravacao')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        output_dir = Path(caso.path_pasta) / 'gravacoes'
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f'{timestamp}_{recording_id}{extension}'
        output_path = output_dir / filename

        size = 0
        try:
            with output_path.open('wb') as destination:
                for chunk in uploaded_file.chunks():
                    size += len(chunk)
                    destination.write(chunk)
        except OSError as exc:
            raise ScreenRecordingError(f'Nao foi possivel salvar a gravacao: {exc}') from exc

        hash_sha256 = HashService.hash_file(output_path)
        recorded_at = timezone.now().isoformat()
        normalized_metadata = {
            **metadata,
            'filename': filename,
            'size_bytes': size,
            'recorded_at_utc': recorded_at,
            'content_type': getattr(uploaded_file, 'content_type', ''),
        }

        metadata_path = output_path.with_suffix('.json')
        metadata_path.write_text(json.dumps(normalized_metadata, ensure_ascii=False, indent=2), encoding='utf-8')

        return ScreenRecordingResult(
            path=output_path,
            hash_sha256=hash_sha256,
            filename=filename,
            size_bytes=size,
            recorded_at_utc=recorded_at,
            metadata={**normalized_metadata, 'metadata_path': str(metadata_path)},
        )

    def _extension(self, filename: str) -> str:
        extension = Path(filename or '').suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ScreenRecordingError('Formato de video nao permitido. Use WebM ou MP4.')
        return extension

    @staticmethod
    def _safe_identifier(value: str) -> str:
        safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(value)).strip('-')
        return safe[:80] or 'gravacao'
