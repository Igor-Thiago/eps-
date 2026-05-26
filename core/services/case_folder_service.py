import re
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify


class CaseFolderError(Exception):
    pass


class CaseFolderService:
    SUBFOLDERS = (
        'sites',
        'gravacoes',
        'capturas',
        'downloads',
        'copias_forenses',
        'integridade',
    )

    @classmethod
    def create_case_folder(cls, case_name: str, base_path=None) -> Path:
        root = Path(base_path or settings.CASES_ROOT).expanduser()
        folder_name = cls._folder_name(case_name)
        case_path = cls._unique_path(root / folder_name)

        try:
            for subfolder in cls.SUBFOLDERS:
                (case_path / subfolder).mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise CaseFolderError(f'Nao foi possivel criar a estrutura de pastas: {exc}') from exc

        return case_path

    @staticmethod
    def _folder_name(case_name: str) -> str:
        slug = slugify(case_name).strip('-')
        if slug:
            return slug
        return re.sub(r'[^a-zA-Z0-9_-]+', '-', case_name).strip('-') or 'caso'

    @staticmethod
    def _unique_path(path: Path) -> Path:
        if not path.exists():
            return path

        counter = 2
        while True:
            candidate = path.with_name(f'{path.name}-{counter}')
            if not candidate.exists():
                return candidate
            counter += 1
