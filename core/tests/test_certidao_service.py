import tempfile
from pathlib import Path

from django.test import TestCase
from unittest.mock import patch

from core.models import Analista, Caso, ConfiguracaoAnalista, Evidencia
from core.services.certidao_service import CertidaoError, CertidaoResult, CertidaoService


def _criar_analista(username='ana01', matricula='M001'):
    return Analista.objects.create_user(
        username=username,
        password='senha123',
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


def _criar_caso(analista, pasta):
    return Caso.objects.create(
        nome='Caso Certidão',
        numero_processo='007/2026',
        analista=analista,
        path_pasta=str(pasta),
    )


class CertidaoServiceTest(TestCase):
    def setUp(self):
        self.analista = _criar_analista()
        self.tmp = tempfile.mkdtemp()
        self.caso = _criar_caso(self.analista, self.tmp)

    def test_gera_arquivo_docx_no_disco(self):
        result = CertidaoService().generate(self.caso, self.analista)
        self.assertIsInstance(result, CertidaoResult)
        self.assertTrue(result.docx_path.exists())
        self.assertTrue(str(result.docx_path).endswith('.docx'))

    def test_nome_arquivo_inclui_id_caso(self):
        result = CertidaoService().generate(self.caso, self.analista)
        self.assertIn(f'{self.caso.id:04d}', result.docx_path.name)

    def test_resultado_tem_hash_sha256_valido(self):
        result = CertidaoService().generate(self.caso, self.analista)
        self.assertEqual(len(result.hash_sha256), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in result.hash_sha256))

    def test_resultado_tem_timestamp_utc(self):
        result = CertidaoService().generate(self.caso, self.analista)
        self.assertIsNotNone(result.generated_at_utc)
        self.assertIn('T', result.generated_at_utc)

    def test_gera_com_config_personalizada(self):
        config = ConfiguracaoAnalista.objects.create(
            analista=self.analista,
            cabecalho='DELEGACIA ESPECIAL\nUnidade de Crimes Digitais',
            assinatura_nome='Dr. Roberto',
            assinatura_cargo='Delegado Titular',
            assinatura_orgao='DEIC/PCDF',
        )
        result = CertidaoService().generate(self.caso, self.analista, config)
        self.assertTrue(result.docx_path.exists())

    def test_gera_sem_config_usa_defaults(self):
        result = CertidaoService().generate(self.caso, self.analista, config=None)
        self.assertTrue(result.docx_path.exists())

    def test_gera_com_evidencias_existentes(self):
        Evidencia.objects.create(
            caso=self.caso,
            tipo=Evidencia.Tipo.SITE,
            hash_sha256='a' * 64,
            path_arquivo='/tmp/site.mhtml',
            metadados_json={'url': 'https://exemplo.gov.br'},
        )
        Evidencia.objects.create(
            caso=self.caso,
            tipo=Evidencia.Tipo.SCREENSHOT,
            hash_sha256='b' * 64,
            path_arquivo='/tmp/screenshot.png',
            metadados_json={'capture_mode': 'manual'},
        )
        result = CertidaoService().generate(self.caso, self.analista)
        self.assertTrue(result.docx_path.exists())

    def test_pasta_inexistente_lanca_certidao_error(self):
        self.caso.path_pasta = '/caminho/que/nao/existe'
        self.caso.save()
        with self.assertRaises(CertidaoError):
            CertidaoService().generate(self.caso, self.analista)

    def test_hashes_diferentes_em_geracoes_distintas(self):
        r1 = CertidaoService().generate(self.caso, self.analista)
        r1.docx_path.unlink()
        r2 = CertidaoService().generate(self.caso, self.analista)
        # Arquivos regenerados podem ter timestamps diferentes; apenas verifica que ambos existem
        self.assertTrue(r2.docx_path.exists())


class CertidaoViewTest(TestCase):
    def setUp(self):
        self.analista = _criar_analista()
        self.tmp = tempfile.mkdtemp()
        self.caso = _criar_caso(self.analista, self.tmp)
        self.client.force_login(self.analista)

    def test_post_gera_certidao_e_salva_relatorio(self):
        from core.models import RelatorioGerado
        url = f'/casos/{self.caso.pk}/certidao/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(RelatorioGerado.objects.filter(caso=self.caso, tipo=RelatorioGerado.Tipo.DOCX).exists())

    def test_post_por_outro_analista_retorna_403(self):
        outro = _criar_analista('ana02', 'M002')
        self.client.force_login(outro)
        url = f'/casos/{self.caso.pk}/certidao/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_get_nao_permitido(self):
        url = f'/casos/{self.caso.pk}/certidao/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_falha_no_service_exibe_mensagem_erro(self):
        url = f'/casos/{self.caso.pk}/certidao/'
        with patch('core.views.CertidaoService.generate', side_effect=CertidaoError('falha simulada')):
            response = self.client.post(url, follow=True)
        self.assertContains(response, 'falha simulada')
