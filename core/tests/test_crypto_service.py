import tempfile
from pathlib import Path

from cryptography.exceptions import InvalidTag
from django.test import SimpleTestCase

from core.services.crypto_service import CryptoService
from core.services.hash_service import HashService


SENHA = b'senha-super-secreta-pcdf'


class EncryptDecryptBytesTest(SimpleTestCase):
    def setUp(self):
        self.salt = CryptoService.gerar_salt()

    def test_cifrar_decifrar_retorna_original(self):
        original = b'evidencia digital confidencial'
        cifrado = CryptoService.encrypt_bytes(original, SENHA, self.salt)
        self.assertEqual(CryptoService.decrypt_bytes(cifrado, SENHA, self.salt), original)

    def test_cifrado_diferente_do_original(self):
        original = b'conteudo da evidencia'
        cifrado = CryptoService.encrypt_bytes(original, SENHA, self.salt)
        self.assertNotEqual(cifrado, original)

    def test_chave_errada_levanta_invalid_tag(self):
        cifrado = CryptoService.encrypt_bytes(b'dado secreto', SENHA, self.salt)
        with self.assertRaises(InvalidTag):
            CryptoService.decrypt_bytes(cifrado, b'senha-errada', self.salt)

    def test_salt_errado_levanta_invalid_tag(self):
        cifrado = CryptoService.encrypt_bytes(b'dado secreto', SENHA, self.salt)
        outro_salt = CryptoService.gerar_salt()
        with self.assertRaises(InvalidTag):
            CryptoService.decrypt_bytes(cifrado, SENHA, outro_salt)

    def test_dois_cifrados_do_mesmo_dado_sao_diferentes(self):
        """Nonce aleatório garante que cifrar duas vezes gera resultados distintos."""
        original = b'mesmo conteudo'
        cifrado1 = CryptoService.encrypt_bytes(original, SENHA, self.salt)
        cifrado2 = CryptoService.encrypt_bytes(original, SENHA, self.salt)
        self.assertNotEqual(cifrado1, cifrado2)

    def test_salt_aleatorio_unico(self):
        self.assertNotEqual(CryptoService.gerar_salt(), CryptoService.gerar_salt())


class EncryptDecryptFileTest(SimpleTestCase):
    def setUp(self):
        self.salt = CryptoService.gerar_salt()

    def test_cifrar_arquivo_e_decifrar_retorna_original(self):
        conteudo = b'screenshot da evidencia digital'
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(conteudo)
            path = f.name

        cifrado = CryptoService.encrypt_file(path, SENHA, self.salt)
        self.assertEqual(CryptoService.decrypt_bytes(cifrado, SENHA, self.salt), conteudo)

    def test_hash_calculado_antes_da_cifracao(self):
        """Hash do original deve bater com hash do decifrado, não do cifrado."""
        conteudo = b'video forense mp4'
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(conteudo)
            path = f.name

        hash_original = HashService.hash_file(path)
        cifrado = CryptoService.encrypt_file(path, SENHA, self.salt)
        decifrado = CryptoService.decrypt_bytes(cifrado, SENHA, self.salt)

        hash_decifrado = HashService.hash_bytes(decifrado)
        self.assertEqual(hash_original, hash_decifrado)

    def test_arquivo_cifrado_nao_legivel_sem_chave(self):
        conteudo = b'dado sensivel'
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(conteudo)
            path = f.name

        cifrado = CryptoService.encrypt_file(path, SENHA, self.salt)
        self.assertNotIn(conteudo, cifrado)

    def test_chave_errada_no_arquivo_levanta_invalid_tag(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'conteudo qualquer')
            path = f.name

        cifrado = CryptoService.encrypt_file(path, SENHA, self.salt)
        with self.assertRaises(InvalidTag):
            CryptoService.decrypt_bytes(cifrado, b'chave-invalida', self.salt)
