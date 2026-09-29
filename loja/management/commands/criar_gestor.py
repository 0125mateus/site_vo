import os

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()
SENHA_PADRAO = 'gestor123'


class Command(BaseCommand):
    help = 'Cria usuário gestor para acessar /gestao/ (só se ainda não existir)'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='gestor')
        parser.add_argument('--password', default='gestor123')
        parser.add_argument('--email', default='gestor@vinilpagina.local')

    def handle(self, *args, **options):
        username = options['username']
        password = os.environ.get('GESTOR_PASSWORD') or options['password']

        if not settings.DEBUG and password == SENHA_PADRAO:
            self.stderr.write(self.style.ERROR(
                'Senha padrão recusada em produção. Defina GESTOR_PASSWORD no Render.'
            ))
            return

        existente = User.objects.filter(username=username).first()
        if existente:
            if (
                not settings.DEBUG
                and authenticate(username=username, password=SENHA_PADRAO)
            ):
                self.stderr.write(self.style.ERROR(
                    f'O usuário "{username}" ainda usa a senha padrão. '
                    'Troque em /gestao/ antes de vender.'
                ))
            else:
                self.stdout.write(self.style.WARNING(f'Usuário "{username}" já existe.'))
            return

        user = User.objects.create_superuser(
            username=username,
            email=options['email'],
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f'Gestor criado: {user.username}'))
        if settings.DEBUG:
            self.stdout.write(f'  Senha: {password}')
        self.stdout.write('  Acesse: /gestao/entrar/')
        self.stdout.write(self.style.WARNING('  Troque a senha depois do primeiro acesso.'))
