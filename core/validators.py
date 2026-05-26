import logging
from pathlib import PurePath

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger('PCDF_SecOps')

EXTENSOES_PERIGOSAS = {'.vbs', '.exe', '.bat', '.sh'}


class ColetaVestigioInput(BaseModel):
    nome_arquivo: str = Field(..., min_length=1, max_length=255)

    @field_validator('nome_arquivo')
    @classmethod
    def bloquear_extensoes_perigosas(cls, value: str) -> str:
        extensao = PurePath(value.strip()).suffix.lower()
        if extensao in EXTENSOES_PERIGOSAS:
            logger.warning('Extensao proibida detectada: %s', value)
            raise ValueError('Extensao de arquivo nao permitida.')
        return value


def validar_nome_arquivo(nome_arquivo: str) -> ColetaVestigioInput:
    return ColetaVestigioInput(nome_arquivo=nome_arquivo)
