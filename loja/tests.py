import hashlib
import hmac
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import ItemPedido, Livro, MidiaAudiovisual, Musica, Pagamento, Pedido, PlanoClube, Produto

User = get_user_model()


def _build_signature(secret, data_id, request_id, ts):
    manifest = f'id:{data_id};request-id:{request_id};ts:{ts};'
    v1 = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f'ts={ts},v1={v1}'


@override_settings(MERCADOPAGO_WEBHOOK_SECRET='test-webhook-secret')
class MercadoPagoWebhookViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='cliente',
            password='senha123',
            email='cliente@example.com',
        )
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

    @patch('loja.email_service.enviar_email_pedido_aprovado')
    @patch('loja.views.buscar_pagamento')
    def test_webhook_aprovado_atualiza_pedido(self, mock_buscar, mock_email):
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
        mock_email.assert_called_once()
        args, _ = mock_email.call_args
        self.assertEqual(args[0].pk, self.pedido.pk)

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
        mock_criar.return_value = {
            'preference_id': 'pref-123',
            'init_point': 'https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=pref-123',
            'sandbox_init_point': '',
        }

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['preference_id'], 'pref-123')
        self.assertEqual(response.data['public_key'], 'TEST_PUBLIC_KEY')
        self.assertIn('mercadopago.com', response.data['init_point'])
        self.assertEqual(response.data['checkout_url'], response.data['init_point'])


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


class PedidoEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='comprador',
            password='senha123',
            email='comprador@example.com',
        )
        self.produto = Produto.objects.create(
            titulo='Disco Teste',
            preco=Decimal('29.90'),
            estoque=3,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user,
            valor_total=Decimal('29.90'),
            status=Pedido.STATUS_AGUARDANDO,
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco_unitario=self.produto.preco,
        )

    @patch('loja.email_service.EmailMultiAlternatives.send')
    def test_envia_email_quando_aprovado(self, mock_send):
        from loja.mercadopago_service import aplicar_pagamento_ao_pedido

        aplicar_pagamento_ao_pedido(self.pedido, {
            'id': 'pay-1',
            'status': 'approved',
            'transaction_amount': 29.90,
        })
        mock_send.assert_called_once()

    @patch('loja.email_service.EmailMultiAlternatives.send')
    def test_nao_reenvia_email_se_ja_aprovado(self, mock_send):
        from loja.mercadopago_service import aplicar_pagamento_ao_pedido

        self.pedido.status = Pedido.STATUS_APROVADO
        self.pedido.save(update_fields=['status'])

        aplicar_pagamento_ao_pedido(self.pedido, {
            'id': 'pay-2',
            'status': 'approved',
            'transaction_amount': 29.90,
        })
        mock_send.assert_not_called()

    @patch('loja.email_service.EmailMultiAlternatives.send')
    def test_sem_email_do_cliente_nao_envia(self, mock_send):
        from loja.email_service import enviar_email_pedido_aprovado

        self.user.email = ''
        self.user.save(update_fields=['email'])

        enviado = enviar_email_pedido_aprovado(self.pedido)
        self.assertFalse(enviado)
        mock_send.assert_not_called()


class PromocoesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='combo_user',
            password='senha123',
            email='combo@example.com',
        )
        self.disco = Musica.objects.create(
            titulo='Disco Combo',
            artista='Artista',
            preco=Decimal('100.00'),
            estoque=5,
            ativo=True,
        )
        self.livro = Livro.objects.create(
            titulo='Livro Combo',
            autor='Autor',
            preco=Decimal('50.00'),
            estoque=5,
            ativo=True,
        )
        self.plano = PlanoClube.objects.create(
            titulo='Clube Teste',
            preco_mensal=Decimal('29.90'),
            desconto_extra_percent=5,
            ativo=True,
        )

    def test_desconto_combo_livro_disco(self):
        from loja.promocoes import calcular_promocoes_carrinho

        itens = [
            {
                'produto': self.disco,
                'modalidade': 'venda',
                'preco_unitario': self.disco.preco,
                'subtotal': self.disco.preco,
                'quantidade': 1,
            },
            {
                'produto': self.livro,
                'modalidade': 'venda',
                'preco_unitario': self.livro.preco,
                'subtotal': self.livro.preco,
                'quantidade': 1,
            },
        ]
        promos = calcular_promocoes_carrinho(self.user, itens)
        self.assertTrue(promos['tem_combo'])
        self.assertEqual(promos['desconto_combo'], Decimal('15.00'))

    def test_ativar_assinatura_clube(self):
        from datetime import timedelta

        from loja.promocoes import ativar_assinatura_clube

        pedido = Pedido.objects.create(
            cliente=self.user,
            plano_clube=self.plano,
            valor_total=self.plano.preco_mensal,
        )
        assinatura = ativar_assinatura_clube(pedido)
        self.assertIsNotNone(assinatura)
        self.assertEqual(assinatura.plano_id, self.plano.pk)
        self.assertGreaterEqual(
            assinatura.valido_ate,
            timezone.localdate() + timedelta(days=29),
        )


class CriarPreferenciaClubeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='assinante', password='senha123')
        self.client.force_authenticate(user=self.user)
        self.plano = PlanoClube.objects.create(
            titulo='Clube Solo',
            preco_mensal=Decimal('29.90'),
            ativo=True,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user,
            valor_total=self.plano.preco_mensal,
            plano_clube=self.plano,
        )
        self.url = reverse('criar_preferencia_pagamento', kwargs={'pedido_id': self.pedido.pk})

    @patch('loja.views.criar_preferencia_pagamento')
    @override_settings(MERCADOPAGO_PUBLIC_KEY='TEST_PUBLIC_KEY')
    def test_pedido_so_clube_cria_preferencia(self, mock_criar):
        mock_criar.return_value = 'pref-clube'

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['preference_id'], 'pref-clube')


class NewsletterTests(TestCase):
    def test_inscricao_newsletter(self):
        response = self.client.post(reverse('inscrever_newsletter'), {'email': 'novo@example.com'})
        self.assertEqual(response.status_code, 302)
        from loja.models import InscricaoNewsletter
        self.assertTrue(InscricaoNewsletter.objects.filter(email='novo@example.com').exists())


class AvaliacaoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='avaliador', password='senha123')
        self.produto = Produto.objects.create(titulo='Item', preco=Decimal('10'), estoque=1, ativo=True)

    def test_avaliar_produto(self):
        self.client.force_login(self.user)
        url = reverse('avaliar_produto', kwargs={'produto_id': self.produto.pk})
        response = self.client.post(url, {'nota': 5, 'comentario': 'Ótimo!'})
        self.assertEqual(response.status_code, 302)
        from loja.models import Avaliacao
        av = Avaliacao.objects.get(usuario=self.user, produto=self.produto)
        self.assertEqual(av.nota, 5)


class MediaUploadPathTests(TestCase):
    def test_nome_arquivo_remove_espacos(self):
        from loja.models import _nome_arquivo_seguro, produto_imagem_upload_path

        self.assertEqual(
            _nome_arquivo_seguro('ChatGPT Image 14 de ago.png'),
            'chatgpt-image-14-de-ago.png',
        )
        produto = Produto(pk=7, titulo='x', preco=Decimal('1'))
        path = produto_imagem_upload_path(produto, 'Capa Com Espaço.JPG')
        self.assertEqual(path, 'produtos/7/capa-com-espaco.jpg')


class GestaoExcluirMidiaTests(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user(
            username='gestor', password='senha', is_staff=True,
        )
        self.cliente = User.objects.create_user(username='cliente', password='senha')
        self.midia = MidiaAudiovisual.objects.create(
            titulo='Filme Teste',
            preco=Decimal('29.90'),
            estoque=3,
            tipo=MidiaAudiovisual.Tipo.FILME,
        )
        self.url = reverse('gestao_midia_excluir', kwargs={'pk': self.midia.pk})
        self.client.force_login(self.gestor)

    def test_excluir_midia_sem_pedido(self):
        response = self.client.post(self.url, {'acao': 'excluir'})
        self.assertRedirects(response, reverse('gestao_midias_lista'))
        self.assertFalse(MidiaAudiovisual.objects.filter(pk=self.midia.pk).exists())

    def test_excluir_midia_com_pedido_nao_quebra(self):
        pedido = Pedido.objects.create(cliente=self.cliente, valor_total=Decimal('29.90'))
        ItemPedido.objects.create(
            pedido=pedido,
            produto=self.midia,
            quantidade=1,
            preco_unitario=self.midia.preco,
        )
        response = self.client.post(self.url, {'acao': 'excluir'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MidiaAudiovisual.objects.filter(pk=self.midia.pk).exists())

    def test_desativar_midia_com_pedido(self):
        pedido = Pedido.objects.create(cliente=self.cliente, valor_total=Decimal('29.90'))
        ItemPedido.objects.create(
            pedido=pedido,
            produto=self.midia,
            quantidade=1,
            preco_unitario=self.midia.preco,
        )
        response = self.client.post(self.url, {'acao': 'desativar'})
        self.assertRedirects(response, reverse('gestao_midias_lista'))
        self.midia.refresh_from_db()
        self.assertFalse(self.midia.ativo)


class CheckoutPagamentoJsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cliente', password='senha')
        self.produto = Produto.objects.create(
            titulo='luna24', preco=Decimal('1.00'), estoque=5, ativo=True,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user,
            valor_total=Decimal('1.00'),
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco_unitario=self.produto.preco,
        )
        self.client.force_login(self.user)

    def test_valor_no_javascript_usa_ponto(self):
        response = self.client.get(reverse('checkout', kwargs={'pedido_id': self.pedido.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "create('wallet', 'payment-brick-container'")
        self.assertNotContains(response, 'amount: 1,00')


class ProcessarPagamentoBrickViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='comprador', password='senha123', email='comprador@example.com',
        )
        self.client.force_authenticate(user=self.user)
        self.produto = Produto.objects.create(
            titulo='Livro Teste', preco=Decimal('39.90'), estoque=5,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user, valor_total=Decimal('39.90'),
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco_unitario=self.produto.preco,
        )
        self.url = reverse('processar_pagamento_brick', kwargs={'pedido_id': self.pedido.pk})

    @patch('loja.views.criar_pagamento_com_brick')
    def test_processa_formdata_do_brick(self, mock_criar):
        mock_criar.return_value = {'id': 999, 'status': 'approved'}
        response = self.client.post(self.url, {
            'token': 'tok_test',
            'payment_method_id': 'master',
            'installments': 1,
            'payer': {'email': 'comprador@example.com'},
        }, format='json')
        self.assertEqual(response.status_code, 200)
        mock_criar.assert_called_once()
        pedido_arg, form_arg = mock_criar.call_args[0]
        self.assertEqual(pedido_arg.pk, self.pedido.pk)
        self.assertEqual(form_arg['token'], 'tok_test')

    @patch('loja.views.criar_pagamento_com_brick')
    def test_pix_devolve_qr_na_resposta(self, mock_criar):
        mock_criar.return_value = {
            'id': 555,
            'status': 'pending',
            'point_of_interaction': {
                'transaction_data': {
                    'qr_code': '00020126580014br.gov.bcb.pix',
                    'qr_code_base64': 'abc123',
                }
            },
        }
        response = self.client.post(self.url, {
            'payment_method_id': 'pix',
            'payer': {'email': 'comprador@example.com'},
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pix']['qr_code'], '00020126580014br.gov.bcb.pix')
        self.assertEqual(response.data['payment_id'], '555')


class PayloadBrickTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='comprador', password='senha', email='comprador@example.com',
        )
        self.pedido = Pedido.objects.create(cliente=self.user, valor_total=Decimal('1.00'))

    def test_remove_entity_type_invalido_do_pix(self):
        from loja.mercadopago_service import montar_payload_pagamento_brick

        payload = montar_payload_pagamento_brick(self.pedido, {
            'payment_method_id': 'pix',
            'payer': {
                'email': '0.1.2.5mateus@gmail.com',
                'entity_type': 'guest',
            },
            'token': None,
        })
        self.assertEqual(payload['payment_method_id'], 'pix')
        self.assertEqual(payload['payer']['email'], '0.1.2.5mateus@gmail.com')
        self.assertNotIn('entity_type', payload['payer'])
        self.assertNotIn('token', payload)
