from django.test import TestCase

from core.models import Analista, AuditLog, Caso
from core.services.audit_logger import AuditLogger


def _criar_analista(username='ana01', matricula='M001'):
    return Analista.objects.create_user(
        username=username,
        password='senha123',
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


def _criar_caso(analista, nome='Caso Teste'):
    return Caso.objects.create(
        nome=nome,
        numero_processo='001/2026',
        analista=analista,
        path_pasta='/tmp/caso_teste',
    )


class AuditLoggerLogTest(TestCase):
    def setUp(self):
        self.analista = _criar_analista()
        self.caso = _criar_caso(self.analista)

    def test_primeiro_bloco_tem_hash_anterior_nulo(self):
        log = AuditLogger.log(self.caso, self.analista, 'CASO_ABERTO')
        self.assertIsNone(log.hash_bloco_anterior)
        self.assertIsNotNone(log.hash_bloco_atual)

    def test_segundo_bloco_referencia_hash_do_anterior(self):
        log1 = AuditLogger.log(self.caso, self.analista, 'CASO_ABERTO')
        log2 = AuditLogger.log(self.caso, self.analista, 'SITE_PRESERVADO', {'url': 'http://exemplo.com'})
        self.assertEqual(log2.hash_bloco_anterior, log1.hash_bloco_atual)

    def test_acoes_diferentes_geram_hashes_diferentes(self):
        log1 = AuditLogger.log(self.caso, self.analista, 'ACAO_A')
        log2 = AuditLogger.log(self.caso, self.analista, 'ACAO_B')
        self.assertNotEqual(log1.hash_bloco_atual, log2.hash_bloco_atual)

    def test_dados_json_salvos_corretamente(self):
        dados = {'url': 'http://pcdf.df.gov.br', 'ip': '200.0.0.1'}
        log = AuditLogger.log(self.caso, self.analista, 'SITE_PRESERVADO', dados)
        self.assertEqual(log.dados_json, dados)

    def test_logs_isolados_por_caso(self):
        analista2 = _criar_analista('ana02', 'M002')
        caso2 = _criar_caso(analista2, 'Outro Caso')

        AuditLogger.log(self.caso, self.analista, 'ACAO_CASO_1')
        log_caso2 = AuditLogger.log(caso2, analista2, 'ACAO_CASO_2')

        self.assertIsNone(log_caso2.hash_bloco_anterior)


class VerificarCadeiaTest(TestCase):
    def setUp(self):
        self.analista = _criar_analista()
        self.caso = _criar_caso(self.analista)

    def test_cadeia_vazia_e_valida(self):
        self.assertTrue(AuditLogger.verificar_cadeia(self.caso))

    def test_cadeia_integra_com_multiplos_blocos(self):
        AuditLogger.log(self.caso, self.analista, 'CASO_ABERTO')
        AuditLogger.log(self.caso, self.analista, 'SITE_PRESERVADO')
        AuditLogger.log(self.caso, self.analista, 'GRAVACAO_INICIADA')
        self.assertTrue(AuditLogger.verificar_cadeia(self.caso))

    def test_adulteracao_no_hash_detectada(self):
        AuditLogger.log(self.caso, self.analista, 'CASO_ABERTO')
        log2 = AuditLogger.log(self.caso, self.analista, 'SITE_PRESERVADO')
        AuditLogger.log(self.caso, self.analista, 'GRAVACAO_INICIADA')

        log2.hash_bloco_atual = 'a' * 64
        log2.save()

        self.assertFalse(AuditLogger.verificar_cadeia(self.caso))

    def test_adulteracao_no_hash_anterior_detectada(self):
        AuditLogger.log(self.caso, self.analista, 'CASO_ABERTO')
        log2 = AuditLogger.log(self.caso, self.analista, 'SITE_PRESERVADO')

        log2.hash_bloco_anterior = 'b' * 64
        log2.save()

        self.assertFalse(AuditLogger.verificar_cadeia(self.caso))

    def test_adulteracao_nos_dados_detectada(self):
        AuditLogger.log(self.caso, self.analista, 'CASO_ABERTO')
        log2 = AuditLogger.log(self.caso, self.analista, 'SITE_PRESERVADO', {'url': 'http://original.com'})

        log2.dados_json = {'url': 'http://adulterado.com'}
        log2.save()

        self.assertFalse(AuditLogger.verificar_cadeia(self.caso))
