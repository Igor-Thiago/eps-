from django.test import TestCase
from django.urls import reverse

from core.models import Analista, ConfiguracaoAnalista


def _criar_analista(username='ana01', matricula='M001', password='senha123'):
    return Analista.objects.create_user(
        username=username,
        password=password,
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


class ConfiguracaoAnalistaModelTest(TestCase):
    def setUp(self):
        self.analista = _criar_analista()

    def test_criacao_com_defaults(self):
        config = ConfiguracaoAnalista.objects.create(analista=self.analista)
        self.assertEqual(config.intervalo_screenshot, 0)
        self.assertTrue(config.incluir_info_tecnica)
        self.assertEqual(config.assinatura_orgao, 'CORF/PCDF')
        self.assertIn('POLÍCIA CIVIL', config.cabecalho)

    def test_str_inclui_analista(self):
        config = ConfiguracaoAnalista.objects.create(analista=self.analista)
        self.assertIn('Config', str(config))

    def test_relacao_onetoone_com_analista(self):
        config = ConfiguracaoAnalista.objects.create(analista=self.analista)
        self.assertEqual(self.analista.configuracao, config)

    def test_segunda_config_para_mesmo_analista_falha(self):
        ConfiguracaoAnalista.objects.create(analista=self.analista)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ConfiguracaoAnalista.objects.create(analista=self.analista)

    def test_updated_at_atualizado_ao_salvar(self):
        config = ConfiguracaoAnalista.objects.create(analista=self.analista)
        ts_antes = config.updated_at
        config.cabecalho = 'NOVO CABEÇALHO'
        config.save()
        config.refresh_from_db()
        self.assertGreaterEqual(config.updated_at, ts_antes)


class ConfiguracaoViewTest(TestCase):
    def setUp(self):
        self.analista = _criar_analista()
        self.client.force_login(self.analista)
        self.url = reverse('configuracao')

    def test_get_retorna_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_cria_config_automaticamente(self):
        self.assertFalse(ConfiguracaoAnalista.objects.filter(analista=self.analista).exists())
        self.client.get(self.url)
        self.assertTrue(ConfiguracaoAnalista.objects.filter(analista=self.analista).exists())

    def test_get_anonimo_redireciona_para_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f'{reverse("login")}?next={self.url}')

    def test_post_salva_configuracoes(self):
        response = self.client.post(self.url, {
            'cabecalho': 'NOVO CABEÇALHO',
            'assinatura_nome': 'Dr. João',
            'assinatura_cargo': 'Delegado',
            'assinatura_orgao': 'PCDF',
            'incluir_info_tecnica': 'on',
            'intervalo_screenshot': '10',
            'pasta_padrao': '',
            'tab': 'geral',
        })
        self.assertRedirects(response, f'{self.url}?tab=geral')
        config = ConfiguracaoAnalista.objects.get(analista=self.analista)
        self.assertEqual(config.cabecalho, 'NOVO CABEÇALHO')
        self.assertEqual(config.assinatura_nome, 'Dr. João')
        self.assertEqual(config.intervalo_screenshot, 10)

    def test_post_preserva_tab_ativa_no_redirect(self):
        self.client.post(self.url, {
            'cabecalho': 'X',
            'assinatura_nome': '',
            'assinatura_cargo': '',
            'assinatura_orgao': 'CORF/PCDF',
            'incluir_info_tecnica': 'on',
            'intervalo_screenshot': '0',
            'pasta_padrao': '',
            'tab': 'gravacao',
        })
        response = self.client.get(f'{self.url}?tab=gravacao')
        self.assertEqual(response.status_code, 200)

    def test_configuracoes_isoladas_por_analista(self):
        outro = _criar_analista('ana02', 'M002')
        ConfiguracaoAnalista.objects.create(analista=outro, cabecalho='CONFIG OUTRO')
        self.client.post(self.url, {
            'cabecalho': 'CONFIG ANA01',
            'assinatura_nome': '',
            'assinatura_cargo': '',
            'assinatura_orgao': 'CORF/PCDF',
            'incluir_info_tecnica': 'on',
            'intervalo_screenshot': '0',
            'pasta_padrao': '',
            'tab': 'geral',
        })
        config_outro = ConfiguracaoAnalista.objects.get(analista=outro)
        self.assertEqual(config_outro.cabecalho, 'CONFIG OUTRO')
