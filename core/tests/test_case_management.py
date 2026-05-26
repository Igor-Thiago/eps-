from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import Analista, AuditLog, Caso
from core.services.case_folder_service import CaseFolderService


def criar_analista(username='M001', matricula='M001', password='senha123'):
    return Analista.objects.create_user(
        username=username,
        password=password,
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


class CaseFolderServiceTest(TestCase):
    def test_cria_estrutura_de_pastas_do_caso(self):
        with TemporaryDirectory() as tmpdir:
            case_path = CaseFolderService.create_case_folder('Operacao Alfa', tmpdir)

            self.assertEqual(case_path.name, 'operacao-alfa')
            for subfolder in CaseFolderService.SUBFOLDERS:
                self.assertTrue((case_path / subfolder).is_dir())

    def test_evita_colisao_de_nome_de_pasta(self):
        with TemporaryDirectory() as tmpdir:
            first_path = CaseFolderService.create_case_folder('Operacao Alfa', tmpdir)
            second_path = CaseFolderService.create_case_folder('Operacao Alfa', tmpdir)

            self.assertEqual(first_path.name, 'operacao-alfa')
            self.assertEqual(second_path.name, 'operacao-alfa-2')


class CasoManagementViewTest(TestCase):
    def setUp(self):
        self.analista = criar_analista()

    def test_criar_caso_gera_pastas_registro_e_audit_log(self):
        with TemporaryDirectory() as tmpdir, override_settings(CASES_ROOT=Path(tmpdir)):
            self.client.force_login(self.analista)

            response = self.client.post(
                reverse('novo_caso'),
                {'nome': 'Caso Playwright', 'numero_processo': '001/2026'},
            )

            caso = Caso.objects.get(nome='Caso Playwright')
            self.assertRedirects(response, reverse('caso_detalhe', args=[caso.pk]))
            self.assertEqual(caso.analista, self.analista)
            self.assertEqual(caso.numero_processo, '001/2026')
            self.assertTrue(Path(caso.path_pasta).is_dir())
            for subfolder in CaseFolderService.SUBFOLDERS:
                self.assertTrue((Path(caso.path_pasta) / subfolder).is_dir())
            self.assertTrue(AuditLog.objects.filter(caso=caso, acao='CASO_CRIADO').exists())

    def test_criar_caso_permite_pasta_base_personalizada(self):
        with TemporaryDirectory() as tmpdir:
            self.client.force_login(self.analista)

            response = self.client.post(
                reverse('novo_caso'),
                {
                    'nome': 'Caso Customizado',
                    'numero_processo': '',
                    'pasta_base': tmpdir,
                },
            )

            caso = Caso.objects.get(nome='Caso Customizado')
            self.assertRedirects(response, reverse('caso_detalhe', args=[caso.pk]))
            self.assertEqual(Path(caso.path_pasta).parent, Path(tmpdir))

    def test_listagem_exibe_retomar_caso_e_ultimo_acesso(self):
        caso = Caso.objects.create(
            nome='Caso Retomavel',
            numero_processo='002/2026',
            analista=self.analista,
            path_pasta='/tmp/caso_retomavel',
        )
        self.client.force_login(self.analista)

        response = self.client.get(reverse('casos'))

        self.assertContains(response, 'Caso Retomavel')
        self.assertContains(response, 'Retomar')
        self.assertContains(response, reverse('caso_detalhe', args=[caso.pk]))

    def test_retomar_caso_atualiza_ultimo_acesso_e_mostra_barra_inferior(self):
        caso = Caso.objects.create(
            nome='Caso Aberto',
            numero_processo='003/2026',
            analista=self.analista,
            path_pasta='/tmp/caso_aberto',
        )
        self.client.force_login(self.analista)

        response = self.client.get(reverse('caso_detalhe', args=[caso.pk]))
        caso.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(caso.last_accessed_at)
        self.assertContains(response, 'Caso aberto:')
        self.assertContains(response, 'Abrir pasta')

    @patch.dict('os.environ', {'HOST_PROJECT_ROOT': r'C:\Projeto'}, clear=False)
    @patch('core.views.sys.platform', 'linux')
    def test_abrir_pasta_em_docker_windows_exibe_instrucao_manual(self):
        caso = Caso.objects.create(
            nome='Caso Docker',
            numero_processo='004/2026',
            analista=self.analista,
            path_pasta='/app/media/casos/caso-docker',
        )
        self.client.force_login(self.analista)

        response = self.client.get(
            reverse('abrir_pasta', args=[caso.pk]),
            follow=True,
        )

        self.assertContains(response, 'No modo Docker')
        self.assertContains(response, r'C:\Projeto/media/casos/caso-docker')
