import hashlib
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

from core.services.hash_service import HashService


class HashFileTest(SimpleTestCase):
    def test_hash_file_correto(self):
        conteudo = b'evidencia digital pcdf'
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(conteudo)
            path = f.name

        esperado = hashlib.sha256(conteudo).hexdigest()
        self.assertEqual(HashService.hash_file(path), esperado)

    def test_hash_file_diferente_para_conteudos_distintos(self):
        with tempfile.NamedTemporaryFile(delete=False) as f1, \
             tempfile.NamedTemporaryFile(delete=False) as f2:
            f1.write(b'arquivo a')
            f2.write(b'arquivo b')
            path1, path2 = f1.name, f2.name

        self.assertNotEqual(HashService.hash_file(path1), HashService.hash_file(path2))

    def test_hash_arquivo_grande_chunks(self):
        conteudo = b'x' * (HashService._CHUNK_SIZE * 3 + 100)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(conteudo)
            path = f.name

        esperado = hashlib.sha256(conteudo).hexdigest()
        self.assertEqual(HashService.hash_file(path), esperado)


class HashBytesTest(SimpleTestCase):
    def test_hash_bytes_correto(self):
        data = b'pcdf 2026'
        esperado = hashlib.sha256(data).hexdigest()
        self.assertEqual(HashService.hash_bytes(data), esperado)

    def test_hash_bytes_vazio(self):
        esperado = hashlib.sha256(b'').hexdigest()
        self.assertEqual(HashService.hash_bytes(b''), esperado)


class HashZipTest(SimpleTestCase):
    def test_hash_zip_gerado_e_valido(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arq1 = Path(tmpdir) / 'foto.jpg'
            arq2 = Path(tmpdir) / 'pagina.html'
            arq1.write_bytes(b'imagem fake')
            arq2.write_bytes(b'<html>site</html>')

            zip_path = Path(tmpdir) / 'evidencias.zip'
            hash_zip = HashService.hash_zip([arq1, arq2], zip_path)

            self.assertTrue(zip_path.exists())
            self.assertEqual(hash_zip, HashService.hash_file(zip_path))

            with zipfile.ZipFile(zip_path) as zf:
                nomes = zf.namelist()
            self.assertIn('foto.jpg', nomes)
            self.assertIn('pagina.html', nomes)
