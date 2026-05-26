import logging
from pydantic import BaseModel, Field, field_validator, ValidationError

# CONFIGURAÇÃO DE LOGS (Domínio 7 CISSP: Operações)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PCDF_SecOps")

# MODELO DE DADOS COM ZERO TRUST (Domínio 8 CISSP: Desenvolvimento Seguro)
class ColetaVestigio(BaseModel):
    id_analista: int = Field(..., gt=0)
    nome_arquivo: str = Field(..., min_length=5)
    
    @field_validator('nome_arquivo')
    @classmethod
    def bloquear_extensoes_perigosas(cls, v: str) -> str:
        # Proteção contra ataques históricos como ILOVEYOU
        proibidas = ['.vbs', '.exe', '.bat', '.sh']
        if any(v.lower().endswith(ext) for ext in proibidas):
            logger.warning(f"⚠️ BLOQUEIO: Extensão proibida detectada: {v}")
            raise ValueError("Tentativa de injeção de script detectada!")
        return v

def processar_vestigio(dados_brutos: dict):
    try:
        vestigio = ColetaVestigio(**dados_brutos)
        logger.info(f"✅ SUCESSO: '{vestigio.nome_arquivo}' validado pelo Analista {vestigio.id_analista}.")
    except ValidationError as e:
        logger.error(f"❌ FALHA NA VALIDAÇÃO: Dados maliciosos detectados.")
        print(f"Detalhes técnicos: {e.json()}")

if __name__ == "__main__":
    print("\n🚀 PCDF - TESTE DE AMBIENTE SECOPS-FIRST")
    processar_vestigio({"id_analista": 2026, "nome_arquivo": "evidencia_crime.jpg"})
    processar_vestigio({"id_analista": 999, "nome_arquivo": "LOVE-LETTER.vbs"})
