from django.test import SimpleTestCase
from pydantic import ValidationError

from core.validators import validar_nome_arquivo


class ValidarNomeArquivoTest(SimpleTestCase):
    def test_aceita_extensao_segura(self):
        vestigio = validar_nome_arquivo('evidencia.jpg')

        self.assertEqual(vestigio.nome_arquivo, 'evidencia.jpg')

    def test_bloqueia_extensoes_perigosas(self):
        for nome_arquivo in ['payload.vbs', 'instalador.exe', 'script.bat', 'coleta.sh']:
            with self.subTest(nome_arquivo=nome_arquivo):
                with self.assertRaises(ValidationError):
                    validar_nome_arquivo(nome_arquivo)
