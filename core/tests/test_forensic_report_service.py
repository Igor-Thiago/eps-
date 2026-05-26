import base64
import json
from pathlib import Path
from types import SimpleNamespace

from django.test import TestCase

from core.models import Analista, Caso, Evidencia
from core.services.forensic_report_service import ForensicReportService
from core.services.hash_service import HashService


PNG_1X1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
)


class ForensicReportServiceTest(TestCase):
    def setUp(self):
        self.analista = Analista.objects.create_user(
            username='M001',
            password='senha123',
            matricula='M001',
            first_name='Ana',
            last_name='Silva',
        )
        self.caso = Caso.objects.create(
            nome='Caso Relatorio',
            numero_processo='001/2026',
            analista=self.analista,
            path_pasta='/tmp/caso_relatorio',
        )
        self.evidencia = Evidencia.objects.create(
            caso=self.caso,
            tipo=Evidencia.Tipo.SITE,
            hash_sha256='a' * 64,
            path_arquivo='/tmp/caso_relatorio/sites/example.com/20260506_120000/pagina.mhtml',
            metadados_json={},
        )

    def test_gera_pdf_com_hashes_dos_artefatos(self):
        base_dir = Path('/tmp/caso_relatorio_test/sites/example.com/20260506_120000')
        base_dir.mkdir(parents=True, exist_ok=True)
        html_path = base_dir / 'index.html'
        screenshot_path = base_dir / 'screenshot.png'
        mhtml_path = base_dir / 'pagina.mhtml'
        metadata_path = base_dir / 'metadata.json'

        html_path.write_text('<html><title>Example</title></html>', encoding='utf-8')
        screenshot_path.write_bytes(PNG_1X1)
        mhtml_path.write_text('mhtml-data', encoding='utf-8')
        metadata_path.write_text(json.dumps({'url': 'https://example.com'}), encoding='utf-8')

        preservation_result = SimpleNamespace(
            url='https://example.com',
            final_url='https://example.com/',
            domain='example.com',
            output_dir=base_dir,
            html_path=html_path,
            screenshot_path=screenshot_path,
            mhtml_path=mhtml_path,
            metadata_path=metadata_path,
            status=200,
            title='Example',
            technical_metadata={
                'whois_rdap': {'disponivel': True, 'registrar': 'Registrar Brasil'},
                'ssl': {'disponivel': True, 'issuer': {'organizationName': 'DigiCert Inc'}},
                'http_headers': {'disponivel': True, 'status_code': 200, 'headers': {'server': 'nginx'}},
                'dns': {'A': ['93.184.216.34'], 'AAAA': [], 'MX': [], 'NS': []},
                'ip': '93.184.216.34',
            },
        )

        result = ForensicReportService().generate_site_report(self.caso, self.evidencia, preservation_result, 1)

        self.assertTrue(result.pdf_path.exists())
        self.assertEqual(result.report_number, f'RF-{self.caso.id:04d}-001')
        self.assertEqual(result.hash_sha256, HashService.hash_file(result.pdf_path))
        self.assertIn(
            {'name': 'Snapshot MHTML', 'path': str(mhtml_path), 'sha256': HashService.hash_file(mhtml_path)},
            result.artifact_hashes,
        )
