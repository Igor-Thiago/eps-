import base64
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Analista, AuditLog, Caso, Evidencia, RelatorioGerado
from core.services.hash_service import HashService
from core.services.screenshot_service import ScreenshotError, ScreenshotService


PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
)


def criar_analista(username='M001', matricula='M001'):
    return Analista.objects.create_user(
        username=username,
        password='senha123',
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


class ScreenshotServiceTest(TestCase):
    def setUp(self):
        self.analista = criar_analista()

    def test_salva_captura_em_capturas_e_calcula_hash(self):
        with TemporaryDirectory() as tmpdir:
            caso = Caso.objects.create(
                nome='Caso Captura',
                numero_processo='001/2026',
                analista=self.analista,
                path_pasta=tmpdir,
            )
            uploaded = SimpleUploadedFile('captura.png', PNG_1X1, content_type='image/png')

            result = ScreenshotService().save_screenshot(caso, uploaded, {'screenshot_id': 'cap-001'})

            self.assertTrue(result.path.exists())
            self.assertEqual(result.path.parent, Path(tmpdir) / 'capturas')
            self.assertEqual(result.hash_sha256, HashService.hash_file(result.path))
            self.assertTrue(result.path.with_suffix('.json').exists())

    def test_gera_relatorio_individual_da_captura(self):
        with TemporaryDirectory() as tmpdir:
            caso = Caso.objects.create(
                nome='Caso Captura',
                numero_processo='001/2026',
                analista=self.analista,
                path_pasta=tmpdir,
            )
            screenshot_path = Path(tmpdir) / 'capturas' / 'captura.png'
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            screenshot_path.write_bytes(PNG_1X1)
            evidencia = Evidencia.objects.create(
                caso=caso,
                tipo=Evidencia.Tipo.SCREENSHOT,
                hash_sha256=HashService.hash_file(screenshot_path),
                path_arquivo=str(screenshot_path),
                metadados_json={'captured_at_utc': '2026-05-10T12:00:00+00:00'},
            )

            report = ScreenshotService().generate_individual_report(caso, evidencia, 1)

            self.assertTrue(report.pdf_path.exists())
            self.assertEqual(report.hash_sha256, HashService.hash_file(report.pdf_path))

    def test_rejeita_extensao_nao_suportada(self):
        with TemporaryDirectory() as tmpdir:
            caso = Caso.objects.create(
                nome='Caso Captura',
                numero_processo='001/2026',
                analista=self.analista,
                path_pasta=tmpdir,
            )
            uploaded = SimpleUploadedFile('captura.exe', b'binario', content_type='application/octet-stream')

            with self.assertRaises(ScreenshotError):
                ScreenshotService().save_screenshot(caso, uploaded, {'screenshot_id': 'cap-001'})


class ScreenshotCaptureViewTest(TestCase):
    def setUp(self):
        self.analista = criar_analista()
        self.tmpdir = TemporaryDirectory()
        self.caso = Caso.objects.create(
            nome='Caso Captura',
            numero_processo='001/2026',
            analista=self.analista,
            path_pasta=self.tmpdir.name,
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_captura_manual_cria_evidencia_relatorio_e_audit_log(self):
        self.client.force_login(self.analista)
        uploaded = SimpleUploadedFile('cap-001.png', PNG_1X1, content_type='image/png')

        response = self.client.post(
            reverse('criar_captura', args=[self.caso.pk]),
            {
                'screenshot_id': 'cap-001',
                'capture_mode': 'manual',
                'linked_recording_id': '',
                'periodic_interval_seconds': '0',
                'image': uploaded,
            },
        )

        self.assertEqual(response.status_code, 200)
        evidencia = Evidencia.objects.get(caso=self.caso, tipo=Evidencia.Tipo.SCREENSHOT)
        self.assertTrue(Path(evidencia.path_arquivo).exists())
        self.assertEqual(evidencia.hash_sha256, response.json()['hash_sha256'])
        self.assertIn('report_pdf_path', evidencia.metadados_json)
        self.assertTrue(RelatorioGerado.objects.filter(caso=self.caso, tipo=RelatorioGerado.Tipo.PDF).exists())
        self.assertTrue(AuditLog.objects.filter(caso=self.caso, acao='CAPTURA_TELA_REALIZADA').exists())

    def test_captura_vinculada_a_gravacao_nao_gera_relatorio_individual(self):
        self.client.force_login(self.analista)
        uploaded = SimpleUploadedFile('cap-002.png', PNG_1X1, content_type='image/png')

        response = self.client.post(
            reverse('criar_captura', args=[self.caso.pk]),
            {
                'screenshot_id': 'cap-002',
                'capture_mode': 'periodica',
                'linked_recording_id': 'rec-001',
                'periodic_interval_seconds': '5',
                'image': uploaded,
            },
        )

        self.assertEqual(response.status_code, 200)
        evidencia = Evidencia.objects.get(caso=self.caso, tipo=Evidencia.Tipo.SCREENSHOT)
        self.assertEqual(evidencia.metadados_json['linked_recording_id'], 'rec-001')
        self.assertNotIn('report_pdf_path', evidencia.metadados_json)
        self.assertFalse(RelatorioGerado.objects.exists())

    def test_finalizar_video_agrega_capturas_vinculadas(self):
        self.client.force_login(self.analista)
        screenshot_path = Path(self.tmpdir.name) / 'capturas' / 'cap-003.png'
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(PNG_1X1)
        screenshot = Evidencia.objects.create(
            caso=self.caso,
            tipo=Evidencia.Tipo.SCREENSHOT,
            hash_sha256=HashService.hash_file(screenshot_path),
            path_arquivo=str(screenshot_path),
            metadados_json={'linked_recording_id': 'rec-003'},
        )
        uploaded = SimpleUploadedFile('rec-003.webm', b'conteudo-video', content_type='video/webm')

        response = self.client.post(
            reverse('finalizar_gravacao', args=[self.caso.pk]),
            {
                'recording_id': 'rec-003',
                'duration_ms': '1000',
                'mime_type': 'video/webm',
                'video': uploaded,
            },
        )

        self.assertEqual(response.status_code, 200)
        video = Evidencia.objects.get(caso=self.caso, tipo=Evidencia.Tipo.VIDEO)
        self.assertIn(screenshot.id, video.metadados_json['linked_screenshot_ids'])
