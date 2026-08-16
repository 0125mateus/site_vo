import hashlib
import hmac
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .models import ItemPedido, Pagamento, Pedido, Produto

User = get_user_model()


def _build_signature(secret, data_id, request_id, ts):
    manifest = f'id:{data_id};request-id:{request_id};ts:{ts};'
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f'ts={ts},v1={v1}'


@override_settings(MERCADOPAGO_WEBHOOK_SECRET='test-webhook-secret')
class MercadoPagoWebhookViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='cliente', password='senha123')
        self.produto = Produto.objects.create(
            titulo='Disco Teste',
            preco=Decimal('49.90'),
            estoque=10,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user,
            valor_total=Decimal('49.90'),
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco_unitario=self.produto.preco,
        )
        self.url = reverse('mercadopago_webhook')
        self.payment_id = '123456789'
        self.request_id = 'req-abc'
        self.ts = '1704908010'

    def _post_webhook(self, payment_id=None, signature=None, request_id=None):
        payment_id = payment_id or self.payment_id
        request_id = request_id or self.request_id
        signature = signature or _build_signature(
            'test-webhook-secret',
            payment_id,
            request_id,
            self.ts,
        )
        return self.client.post(
            f'{self.url}?data.id={payment_id}&type=payment',
            {'type': 'payment', 'data': {'id': payment_id}},
            format='json',
            HTTP_X_SIGNATURE=signature,
            HTTP_X_REQUEST_ID=request_id,
        )

    @patch('loja.views.buscar_pagamento')
    def test_webhook_aprovado_atualiza_pedido(self, mock_buscar):
        mock_buscar.return_value = {
            'id': self.payment_id,
            'status': 'approved',
            'external_reference': str(self.pedido.pk),
            'payment_type_id': 'credit_card',
            'transaction_amount': 49.90,
        }

        response = self._post_webhook()
        self.assertEqual(response.status_code, 200)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.STATUS_APROVADO)

        pagamento = Pagamento.objects.get(pedido=self.pedido)
        self.assertEqual(pagamento.mercadopago_payment_id, self.payment_id)
        self.assertEqual(pagamento.status, 'approved')

    @patch('loja.views.buscar_pagamento')
    def test_webhook_payment_id_invalido_retorna_200_sem_atualizar(self, mock_buscar):
        from loja.mercadopago_service import MercadoPagoAPIError

        mock_buscar.side_effect = MercadoPagoAPIError('Pagamento não encontrado')

        response = self._post_webhook(payment_id='invalido')
        self.assertEqual(response.status_code, 200)

        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.STATUS_AGUARDANDO)
        self.assertFalse(Pagamento.objects.filter(pedido=self.pedido).exists())

    def test_webhook_assinatura_invalida_retorna_401(self):
        response = self._post_webhook(signature='ts=1,v1=assinatura-invalida')
        self.assertEqual(response.status_code, 401)


class CriarPreferenciaPagamentoViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='comprador', password='senha123')
        self.client.force_authenticate(user=self.user)
        self.produto = Produto.objects.create(
            titulo='Livro Teste',
            preco=Decimal('39.90'),
            estoque=5,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user,
            valor_total=Decimal('39.90'),
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco_unitario=self.produto.preco,
        )
        self.url = reverse('criar_preferencia_pagamento', kwargs={'pedido_id': self.pedido.pk})

    @patch('loja.views.criar_preferencia_pagamento')
    @override_settings(MERCADOPAGO_PUBLIC_KEY='TEST_PUBLIC_KEY')
    def test_cria_preferencia_com_sucesso(self, mock_criar):
        mock_criar.return_value = 'pref-123'

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['preference_id'], 'pref-123')
        self.assertEqual(response.data['public_key'], 'TEST_PUBLIC_KEY')


class AssistenteAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.gestor = User.objects.create_user(
            username='gestor', password='senha', is_staff=True,
        )

    def test_init_cliente(self):
        response = self.client.get(reverse('assistant_init'), {'audience': 'cliente'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('greeting', response.json())

    def test_init_gestor_requer_staff(self):
        response = self.client.get(reverse('assistant_init'), {'audience': 'gestor'})
        self.assertEqual(response.status_code, 403)

    def test_chat_cliente_modo_guiado(self):
        response = self.client.post(
            reverse('assistant_chat'),
            {'message': 'como comprar', 'audience': 'cliente'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('carrinho', data['reply'].lower())
        self.assertEqual(data['intent'], 'compra')
        self.assertIn(data['source'], ('intent', 'guided'))

    def test_chat_gestor_autenticado(self):
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('assistant_chat'),
            {'message': 'como cadastrar disco', 'audience': 'gestor'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('gestao', data['reply'].lower())
        self.assertEqual(data['intent'], 'cadastro')


class AssistenteIntentTests(TestCase):
    def test_classifica_compra_cliente(self):
        from loja.assistant_intent import classify_intent

        result = classify_intent('como faço para comprar um vinil', 'cliente')
        self.assertEqual(result['intent'], 'compra')
        self.assertGreaterEqual(result['confidence'], 0.3)

    def test_classifica_cadastro_gestor(self):
        from loja.assistant_intent import classify_intent

        result = classify_intent('quero cadastrar um novo livro', 'gestor')
        self.assertEqual(result['intent'], 'cadastro')
        self.assertGreaterEqual(result['confidence'], 0.3)

    def test_classifica_pagamento(self):
        from loja.assistant_intent import classify_intent

        result = classify_intent('aceita pix no mercado pago', 'cliente')
        self.assertEqual(result['intent'], 'pagamento')

    def test_frase_do_banco_melhora_classificacao(self):
        from loja.assistant_intent import classify_intent, invalidate_model_cache
        from loja.models import FraseTreinoAssistente

        FraseTreinoAssistente.objects.create(
            audiencia='cliente',
            intencao='entrega',
            texto='vocês mandam para minas gerais',
        )
        invalidate_model_cache()
        result = classify_intent('vocês mandam para minas gerais', 'cliente')
        self.assertEqual(result['intent'], 'entrega')
