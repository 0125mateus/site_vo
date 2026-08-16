from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria usuário gestor para acessar /gestao/ (só se ainda não existir)'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='gestor')
        parser.add_argument('--password', default='gestor123')
        parser.add_argument('--email', default='gestor@vinilpagina.local')

    def handle(self, *args, **options):
        username = options['username']
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Usuário "{username}" já existe.'))
            return

        user = User.objects.create_superuser(
            username=username,
            email=options['email'],
            password=options['password'],
        )
        self.stdout.write(self.style.SUCCESS(f'Gestor criado: {user.username}'))
        self.stdout.write(f'  Senha: {options["password"]}')
        self.stdout.write('  Acesse: http://localhost:8000/gestao/entrar/')
        self.stdout.write(self.style.WARNING('  Troque a senha depois do primeiro acesso.'))
