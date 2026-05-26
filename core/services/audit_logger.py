import hashlib
import json

from django.utils import timezone

from core.models import AuditLog


class AuditLogger:
    @staticmethod
    def log(caso, analista, acao: str, dados: dict = None) -> AuditLog:
        dados = dados or {}

        ultimo = AuditLog.objects.filter(caso=caso).order_by('timestamp_utc').last()
        hash_anterior = ultimo.hash_bloco_atual if ultimo else None

        timestamp = timezone.now()

        conteudo = (
            f"{hash_anterior}|"
            f"{acao}|"
            f"{timestamp.isoformat()}|"
            f"{json.dumps(dados, sort_keys=True, ensure_ascii=False)}"
        )
        hash_atual = hashlib.sha256(conteudo.encode()).hexdigest()

        return AuditLog.objects.create(
            caso=caso,
            analista=analista,
            acao=acao,
            timestamp_utc=timestamp,
            hash_bloco_anterior=hash_anterior,
            hash_bloco_atual=hash_atual,
            dados_json=dados,
        )

    @staticmethod
    def verificar_cadeia(caso) -> bool:
        logs = list(AuditLog.objects.filter(caso=caso).order_by('timestamp_utc'))

        hash_anterior_esperado = None
        for log in logs:
            if log.hash_bloco_anterior != hash_anterior_esperado:
                return False

            conteudo = (
                f"{log.hash_bloco_anterior}|"
                f"{log.acao}|"
                f"{log.timestamp_utc.isoformat()}|"
                f"{json.dumps(log.dados_json, sort_keys=True, ensure_ascii=False)}"
            )
            hash_calculado = hashlib.sha256(conteudo.encode()).hexdigest()

            if hash_calculado != log.hash_bloco_atual:
                return False

            hash_anterior_esperado = log.hash_bloco_atual

        return True
