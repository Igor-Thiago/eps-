from django.test import TestCase
from django.urls import reverse

from core.models import Analista, Caso


def criar_analista(username='ana01', matricula='M001', password='senha123'):
    return Analista.objects.create_user(
        username=username,
        password=password,
        matricula=matricula,
        first_name='Ana',
        last_name='Silva',
    )


def criar_caso(analista, nome='Caso Teste'):
    return Caso.objects.create(
        nome=nome,
        numero_processo='001/2026',
        analista=analista,
        path_pasta='/tmp/caso_teste',
    )


class RegistroAnalistaTest(TestCase):
    def test_analista_consegue_se_cadastrar_com_senha_hasheada(self):
        response = self.client.post(
            reverse('cadastro'),
            {
                'nome': 'Bruno Lima',
                'matricula': 'PCDF100',
                'senha': 'senha-forte-123',
                'confirmar_senha': 'senha-forte-123',
            },
        )

        self.assertRedirects(response, reverse('casos'))
        analista = Analista.objects.get(matricula='PCDF100')
        self.assertEqual(analista.username, 'PCDF100')
        self.assertTrue(analista.check_password('senha-forte-123'))
        self.assertNotEqual(analista.password, 'senha-forte-123')

    def test_admin_logado_consegue_abrir_tela_de_novo_analista(self):
        admin = Analista.objects.create_user(
            username='ADM001',
            password='senha123',
            matricula='ADM001',
            first_name='Admin',
            role=Analista.Role.ADMIN_PCDF,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('cadastro'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Novo Analista')

    def test_admin_logado_cadastra_analista_sem_trocar_de_sessao(self):
        admin = Analista.objects.create_user(
            username='ADM001',
            password='senha123',
            matricula='ADM001',
            first_name='Admin',
            role=Analista.Role.ADMIN_PCDF,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse('cadastro'),
            {
                'nome': 'Bruno Lima',
                'matricula': 'PCDF100',
                'senha': 'senha-forte-123',
                'confirmar_senha': 'senha-forte-123',
            },
        )

        self.assertRedirects(response, reverse('cadastro'))
        self.assertTrue(Analista.objects.filter(matricula='PCDF100').exists())
        self.assertEqual(int(self.client.session['_auth_user_id']), admin.pk)

    def test_analista_logado_nao_consegue_cadastrar_outro_analista(self):
        analista = criar_analista()
        self.client.force_login(analista)

        response = self.client.get(reverse('cadastro'))

        self.assertEqual(response.status_code, 403)


class LoginAnalistaTest(TestCase):
    def setUp(self):
        self.analista = criar_analista(username='M001', matricula='M001')

    def test_login_valido_redireciona_para_casos(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'M001', 'password': 'senha123'},
        )

        self.assertRedirects(response, reverse('casos'))

    def test_login_invalido_permanece_na_tela_de_login(self):
        response = self.client.post(
            reverse('login'),
            {'username': 'M001', 'password': 'senha-errada'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, 'Acesso do Analista')


class ControleAcessoCasoTest(TestCase):
    def setUp(self):
        self.analista = criar_analista(username='M001', matricula='M001')
        self.outro_analista = criar_analista(username='M002', matricula='M002')
        self.caso_proprio = criar_caso(self.analista, 'Caso Proprio')
        self.caso_alheio = criar_caso(self.outro_analista, 'Caso Alheio')

    def test_listagem_mostra_apenas_casos_do_analista_logado(self):
        self.client.force_login(self.analista)

        response = self.client.get(reverse('casos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Caso Proprio')
        self.assertNotContains(response, 'Caso Alheio')

    def test_acesso_a_caso_alheio_retorna_403(self):
        self.client.force_login(self.analista)

        response = self.client.get(reverse('caso_detalhe', args=[self.caso_alheio.pk]))

        self.assertEqual(response.status_code, 403)

    def test_acesso_a_caso_proprio_retorna_200(self):
        self.client.force_login(self.analista)

        response = self.client.get(reverse('caso_detalhe', args=[self.caso_proprio.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Caso Proprio')
