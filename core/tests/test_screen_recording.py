from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Analista, AuditLog, Caso, Evidencia
from core.services.hash_service import HashService
from core.services.screen_recording_service import ScreenRecordingError, ScreenRecordingService


def criar_analista(username='M001', matricula='M001'):
    return Analista.objects.create_user(
        username=username,
        password='senha123',
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


class ScreenRecordingServiceTest(TestCase):
    def setUp(self):
        self.analista = criar_analista()

    def test_salva_gravacao_em_gravacoes_e_calcula_hash(self):
        with TemporaryDirectory() as tmpdir:
            caso = Caso.objects.create(
                nome='Caso Gravacao',
                numero_processo='001/2026',
                analista=self.analista,
                path_pasta=tmpdir,
            )
            uploaded = SimpleUploadedFile('gravacao.webm', b'video-webm', content_type='video/webm')

            result = ScreenRecordingService().save_recording(caso, uploaded, {'recording_id': 'abc-123'})

            self.assertTrue(result.path.exists())
            self.assertEqual(result.path.parent, Path(tmpdir) / 'gravacoes')
            self.assertEqual(result.hash_sha256, HashService.hash_file(result.path))
            self.assertEqual(result.size_bytes, len(b'video-webm'))
            self.assertTrue(result.path.with_suffix('.json').exists())

    def test_rejeita_extensao_nao_suportada(self):
        with TemporaryDirectory() as tmpdir:
            caso = Caso.objects.create(
                nome='Caso Gravacao',
                numero_processo='001/2026',
                analista=self.analista,
                path_pasta=tmpdir,
            )
            uploaded = SimpleUploadedFile('gravacao.exe', b'binario', content_type='application/octet-stream')

            with self.assertRaises(ScreenRecordingError):
                ScreenRecordingService().save_recording(caso, uploaded, {'recording_id': 'abc-123'})


class ScreenRecordingViewsTest(TestCase):
    def setUp(self):
        self.analista = criar_analista()
        self.outro_analista = criar_analista('M002', 'M002')
        self.tmpdir = TemporaryDirectory()
        self.outro_tmpdir = TemporaryDirectory()
        self.caso = Caso.objects.create(
            nome='Caso Gravacao',
            numero_processo='001/2026',
            analista=self.analista,
            path_pasta=self.tmpdir.name,
        )
        self.caso_alheio = Caso.objects.create(
            nome='Caso Alheio',
            numero_processo='002/2026',
            analista=self.outro_analista,
            path_pasta=self.outro_tmpdir.name,
        )

    def tearDown(self):
        self.tmpdir.cleanup()
        self.outro_tmpdir.cleanup()

    def test_iniciar_gravacao_registra_audit_log(self):
        self.client.force_login(self.analista)

        response = self.client.post(
            reverse('iniciar_gravacao', args=[self.caso.pk]),
            {
                'recording_id': 'rec-001',
                'microphone_label': 'Microfone Teste',
                'system_audio_requested': 'true',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['recording_id'], 'rec-001')
        self.assertTrue(AuditLog.objects.filter(caso=self.caso, acao='GRAVACAO_INICIADA').exists())

    def test_finalizar_gravacao_cria_evidencia_video_e_log(self):
        self.client.force_login(self.analista)
        uploaded = SimpleUploadedFile('rec-001.webm', b'conteudo-video', content_type='video/webm')

        response = self.client.post(
            reverse('finalizar_gravacao', args=[self.caso.pk]),
            {
                'recording_id': 'rec-001',
                'started_at_utc': '2026-05-10T12:00:00+00:00',
                'duration_ms': '1500',
                'microphone_label': 'Microfone Teste',
                'system_audio_requested': 'true',
                'mime_type': 'video/webm',
                'video': uploaded,
            },
        )

        self.assertEqual(response.status_code, 200)
        evidencia = Evidencia.objects.get(caso=self.caso, tipo=Evidencia.Tipo.VIDEO)
        self.assertTrue(Path(evidencia.path_arquivo).exists())
        self.assertEqual(evidencia.hash_sha256, response.json()['hash_sha256'])
        self.assertEqual(evidencia.metadados_json['recording_id'], 'rec-001')
        self.assertTrue(AuditLog.objects.filter(caso=self.caso, acao='GRAVACAO_FINALIZADA').exists())

    def test_finalizar_gravacao_sem_arquivo_retorna_400(self):
        self.client.force_login(self.analista)

        response = self.client.post(
            reverse('finalizar_gravacao', args=[self.caso.pk]),
            {'recording_id': 'rec-001'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Evidencia.objects.filter(tipo=Evidencia.Tipo.VIDEO).exists())

    def test_gravacao_de_caso_alheio_retorna_403(self):
        self.client.force_login(self.analista)

        response = self.client.post(
            reverse('iniciar_gravacao', args=[self.caso_alheio.pk]),
            {'recording_id': 'rec-001'},
        )

        self.assertEqual(response.status_code, 403)
