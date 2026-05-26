import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


_ITERATIONS = 600_000
_KEY_LENGTH = 32  # 256 bits


def _derivar_chave(senha: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LENGTH,
        salt=salt,
        iterations=_ITERATIONS,
    )
    return kdf.derive(senha)


class CryptoService:
    @staticmethod
    def gerar_salt() -> bytes:
        return os.urandom(16)

    @staticmethod
    def encrypt_file(path: str, senha: bytes, salt: bytes) -> bytes:
        """Cifra o arquivo com AES-256-GCM. Retorna nonce + ciphertext (com tag GCM embutida)."""
        chave = _derivar_chave(senha, salt)
        aesgcm = AESGCM(chave)
        nonce = os.urandom(12)

        with open(path, 'rb') as f:
            plaintext = f.read()

        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    @staticmethod
    def decrypt_file(dados_cifrados: bytes, senha: bytes, salt: bytes) -> bytes:
        """Decifra dados produzidos por encrypt_file. Lança InvalidTag se a chave for errada."""
        chave = _derivar_chave(senha, salt)
        aesgcm = AESGCM(chave)
        nonce = dados_cifrados[:12]
        ciphertext = dados_cifrados[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)

    @staticmethod
    def encrypt_bytes(plaintext: bytes, senha: bytes, salt: bytes) -> bytes:
        """Cifra bytes em memória. Útil para dados que ainda não foram salvos em disco."""
        chave = _derivar_chave(senha, salt)
        aesgcm = AESGCM(chave)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    @staticmethod
    def decrypt_bytes(dados_cifrados: bytes, senha: bytes, salt: bytes) -> bytes:
        chave = _derivar_chave(senha, salt)
        aesgcm = AESGCM(chave)
        nonce = dados_cifrados[:12]
        ciphertext = dados_cifrados[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)
