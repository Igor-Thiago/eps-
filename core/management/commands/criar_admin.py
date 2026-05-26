import getpass

from django.core.management.base import BaseCommand, CommandError

from core.models import Analista


class Command(BaseCommand):
    help = 'Cria uma conta de Administrador PCDF.'

    def add_arguments(self, parser):
        parser.add_argument('--matricula', type=str, help='Matricula do administrador')
        parser.add_argument('--nome', type=str, help='Nome completo do administrador')

    def handle(self, *args, **options):
        matricula = options.get('matricula') or input('Matricula: ').strip()
        nome = options.get('nome') or input('Nome completo: ').strip()

        if not matricula:
            raise CommandError('A matricula nao pode ser vazia.')
        if not nome:
            raise CommandError('O nome nao pode ser vazio.')
        if Analista.objects.filter(matricula=matricula).exists():
            raise CommandError(f'Ja existe um usuario com a matricula "{matricula}".')

        senha = getpass.getpass('Senha: ')
        confirmar = getpass.getpass('Confirmar senha: ')
        if senha != confirmar:
            raise CommandError('As senhas nao conferem.')
        if not senha:
            raise CommandError('A senha nao pode ser vazia.')

        partes = nome.split(maxsplit=1)
        Analista.objects.create_user(
            username=matricula,
            password=senha,
            matricula=matricula,
            first_name=partes[0],
            last_name=partes[1] if len(partes) > 1 else '',
            role=Analista.Role.ADMIN_PCDF,
            is_staff=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Admin "{matricula}" criado com sucesso.'))
