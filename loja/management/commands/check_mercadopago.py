from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import mercadopago


class Command(BaseCommand):
    help = 'Verifica se as credenciais do Mercado Pago estão configuradas e válidas'

    def handle(self, *args, **options):
        erros = []

        if not settings.MERCADOPAGO_ACCESS_TOKEN:
            erros.append('MERCADOPAGO_ACCESS_TOKEN está vazio no .env')
        if not settings.MERCADOPAGO_PUBLIC_KEY:
            erros.append('MERCADOPAGO_PUBLIC_KEY está vazio no .env')
        if not settings.MERCADOPAGO_WEBHOOK_SECRET:
            self.stdout.write(self.style.WARNING(
                'MERCADOPAGO_WEBHOOK_SECRET vazio — webhooks serão rejeitados até configurar.'
            ))

        if erros:
            raise CommandError('\n'.join(erros))

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        response = sdk.payment_methods().list_all()

        if response.get('status') != 200:
            raise CommandError(
                f'Access Token inválido ou expirado (status {response.get("status")}). '
                'Use credenciais de TESTE do painel do Mercado Pago.'
            )

        public_key_prefix = settings.MERCADOPAGO_PUBLIC_KEY[:8]
        self.stdout.write(self.style.SUCCESS('Credenciais OK — Mercado Pago respondeu com sucesso.'))
        self.stdout.write(f'  Public Key: {public_key_prefix}…')
        self.stdout.write(f'  SITE_URL: {settings.SITE_URL}')
        self.stdout.write('')
        self.stdout.write('Próximo passo: teste uma compra em http://localhost:8000')
        self.stdout.write('Para webhook local, use ngrok e atualize SITE_URL no .env')
