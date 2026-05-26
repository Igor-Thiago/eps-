from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from core.models import Analista, AuditLog, Caso, Evidencia, RelatorioGerado
from core.services.site_preserver import SitePreserver


def criar_analista(username='ana01', matricula='M001', password='senha123'):
    return Analista.objects.create_user(
        username=username,
        password=password,
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


def criar_caso(analista, nome='Caso Teste', path_pasta='/tmp/caso_teste'):
    return Caso.objects.create(
        nome=nome,
        numero_processo='001/2026',
        analista=analista,
        path_pasta=path_pasta,
    )


class SitePreserverPathTest(TestCase):
    def test_cria_pasta_sites_por_dominio(self):
        preserver = SitePreserver()
        output_dir = preserver._build_output_dir('/tmp/caso', 'exemplo.com')

        self.assertIn(Path('/tmp/caso/sites/exemplo.com'), output_dir.parents)

    def test_sanitiza_dominio_da_url(self):
        preserver = SitePreserver()

        self.assertEqual(preserver._domain_from_url('https://sub.exemplo.com/pagina'), 'sub.exemplo.com')


class SiteCaptureViewTest(TestCase):
    def setUp(self):
        self.analista = criar_analista(username='M001', matricula='M001')
        self.outro_analista = criar_analista(username='M002', matricula='M002')
        self.caso = criar_caso(self.analista)
        self.caso_alheio = criar_caso(self.outro_analista, 'Caso Alheio', '/tmp/caso_alheio')

    def _resultado_mock(self):
        return SimpleNamespace(
            url='https://example.com',
            final_url='https://example.com/',
            domain='example.com',
            output_dir=Path('/tmp/caso_teste/sites/example.com/20260506_120000'),
            html_path=Path('/tmp/caso_teste/sites/example.com/20260506_120000/index.html'),
            screenshot_path=Path('/tmp/caso_teste/sites/example.com/20260506_120000/screenshot.png'),
            mhtml_path=Path('/tmp/caso_teste/sites/example.com/20260506_120000/pagina.mhtml'),
            metadata_path=Path('/tmp/caso_teste/sites/example.com/20260506_120000/metadata.json'),
            hash_sha256='a' * 64,
            status=200,
            title='Example',
            technical_metadata={},
        )

    def test_capture_cria_evidencia_site_e_log_de_auditoria(self):
        self.client.force_login(self.analista)

        with patch('core.views.SitePreserver') as preserver_cls:
            preserver_cls.return_value.preserve.return_value = self._resultado_mock()
            response = self.client.post(
                reverse('capturar_site', args=[self.caso.pk]),
                {'url': 'https://example.com'},
            )

        self.assertRedirects(response, reverse('caso_detalhe', args=[self.caso.pk]))
        evidencia = Evidencia.objects.get(caso=self.caso, tipo=Evidencia.Tipo.SITE)
        self.assertEqual(evidencia.hash_sha256, 'a' * 64)
        self.assertEqual(evidencia.metadados_json['url'], 'https://example.com')
        self.assertEqual(evidencia.path_arquivo, '/tmp/caso_teste/sites/example.com/20260506_120000/pagina.mhtml')
        self.assertIn('report_pdf_path', evidencia.metadados_json)
        self.assertTrue(RelatorioGerado.objects.filter(caso=self.caso, tipo=RelatorioGerado.Tipo.PDF).exists())
        self.assertTrue(AuditLog.objects.filter(caso=self.caso, acao='SITE_PRESERVADO').exists())

    def test_capture_de_caso_alheio_retorna_403(self):
        self.client.force_login(self.analista)

        response = self.client.post(
            reverse('capturar_site', args=[self.caso_alheio.pk]),
            {'url': 'https://example.com'},
        )

        self.assertEqual(response.status_code, 403)

    def test_url_invalida_nao_chama_preserver(self):
        self.client.force_login(self.analista)

        with patch('core.views.SitePreserver') as preserver_cls:
            response = self.client.post(
                reverse('capturar_site', args=[self.caso.pk]),
                {'url': 'ftp://example.com'},
            )

        self.assertRedirects(response, reverse('caso_detalhe', args=[self.caso.pk]))
        preserver_cls.assert_not_called()
        self.assertFalse(Evidencia.objects.exists())
