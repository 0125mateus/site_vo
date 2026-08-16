from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from loja.models import ItemPedido, Livro, Musica, Pedido

User = get_user_model()


class Command(BaseCommand):
    help = 'Prepara ambiente e verifica requisitos para testar compra com Mercado Pago'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Teste de compra — Mercado Pago ===\n'))

        self._check_env()
        self._check_credenciais()
        self._preparar_dados()
        self._instrucoes()

    def _check_env(self):
        self.stdout.write('1. Variáveis no .env:')
        vars_map = {
            'MERCADOPAGO_ACCESS_TOKEN': settings.MERCADOPAGO_ACCESS_TOKEN,
            'MERCADOPAGO_PUBLIC_KEY': settings.MERCADOPAGO_PUBLIC_KEY,
            'MERCADOPAGO_WEBHOOK_SECRET': settings.MERCADOPAGO_WEBHOOK_SECRET,
            'SITE_URL': settings.SITE_URL,
        }
        for nome, valor in vars_map.items():
            if nome == 'SITE_URL':
                self.stdout.write(f'   {nome}: {valor}')
            elif valor:
                self.stdout.write(self.style.SUCCESS(f'   {nome}: configurado ({valor[:12]}…)'))
            else:
                self.stdout.write(self.style.ERROR(f'   {nome}: VAZIO'))
        self.stdout.write('')

    def _check_credenciais(self):
        self.stdout.write('2. Validação com API Mercado Pago:')
        if not settings.MERCADOPAGO_ACCESS_TOKEN or not settings.MERCADOPAGO_PUBLIC_KEY:
            self.stdout.write(self.style.ERROR(
                '   Pule — preencha ACCESS_TOKEN e PUBLIC_KEY no .env primeiro.\n'
                '   Painel: https://www.mercadopago.com.br/developers/panel/app\n'
                '   Use credenciais de TESTE (não produção).\n'
            ))
            return

        try:
            import mercadopago
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            response = sdk.payment_methods().list_all()
            if response.get('status') == 200:
                self.stdout.write(self.style.SUCCESS('   Credenciais válidas — API respondeu OK.\n'))
            else:
                self.stdout.write(self.style.ERROR(
                    f'   Token rejeitado (status {response.get("status")}). '
                    'Verifique se copiou credenciais de TESTE.\n'
                ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'   Erro ao conectar: {exc}\n'))

    def _preparar_dados(self):
        self.stdout.write('3. Dados de teste na loja:')

        if not Musica.objects.exists() and not Livro.objects.exists():
            self.stdout.write('   Criando produtos demo…')
            from django.core.management import call_command
            call_command('seed_produtos')

        self.stdout.write(f'   Discos: {Musica.objects.filter(ativo=True).count()}')
        self.stdout.write(f'   Livros: {Livro.objects.filter(ativo=True).count()}')

        comprador, created = User.objects.get_or_create(
            username='comprador',
            defaults={'email': 'comprador@teste.local'},
        )
        if created:
            comprador.set_password('comprador123')
            comprador.save()
            self.stdout.write(self.style.SUCCESS('   Usuário comprador criado: comprador / comprador123'))
        else:
            self.stdout.write('   Usuário comprador: comprador / comprador123 (já existe)')

        if not User.objects.filter(username='gestor', is_staff=True).exists():
            self.stdout.write(self.style.WARNING(
                '   Gestor não encontrado. Rode: python manage.py criar_gestor'
            ))
        self.stdout.write('')

    def _instrucoes(self):
        if not settings.MERCADOPAGO_ACCESS_TOKEN or not settings.MERCADOPAGO_PUBLIC_KEY:
            raise CommandError(
                'Configure MERCADOPAGO_ACCESS_TOKEN e MERCADOPAGO_PUBLIC_KEY no .env '
                'e rode este comando novamente.'
            )

        self.stdout.write(self.style.MIGRATE_HEADING('4. Passo a passo do teste:\n'))
        passos = [
            'python manage.py runserver',
            'Abra http://localhost:8000',
            'Clique em um disco ou livro → vai ao carrinho',
            'Login: comprador / comprador123',
            'Clique em Finalizar pedido',
            'No Payment Brick, use cartão de TESTE:',
            '  Número: 5031 4332 1540 6351',
            '  CVV: 123 | Validade: 11/30 | Nome: APRO',
            'Aguarde na página de processamento',
        ]
        for i, p in enumerate(passos, 1):
            self.stdout.write(f'   {i}. {p}')

        self.stdout.write('')
        if not settings.MERCADOPAGO_WEBHOOK_SECRET:
            self.stdout.write(self.style.WARNING(
                'WEBHOOK: MERCADOPAGO_WEBHOOK_SECRET vazio — em DEBUG o status '
                'é sincronizado pela API ao abrir a página de processamento.\n'
                'Para produção ou webhook em tempo real: ngrok + SITE_URL + secret no painel MP.\n'
            ))
        else:
            self.stdout.write('Webhook configurado. Use ngrok se testar notificações locais.\n')

        self.stdout.write(self.style.SUCCESS('Pronto para testar!'))
