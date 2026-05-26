import hashlib
import zipfile
from pathlib import Path


class HashService:
    _CHUNK_SIZE = 8192

    @staticmethod
    def hash_file(path) -> str:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(HashService._CHUNK_SIZE), b''):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def hash_zip(paths, zip_path) -> str:
        """Cria ZIP com os arquivos informados e retorna o SHA-256 do ZIP."""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                zf.write(p, Path(p).name)
        return HashService.hash_file(zip_path)
