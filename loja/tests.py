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

ENDERECO_TESTE = {
    'entrega_nome': 'Cliente Teste',
    'entrega_telefone': '(11) 99999-0000',
    'entrega_cep': '01310-100',
    'entrega_logradouro': 'Avenida Paulista',
    'entrega_numero': '1000',
    'entrega_bairro': 'Bela Vista',
    'entrega_cidade': 'São Paulo',
    'entrega_uf': 'SP',
}


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
        self.assertFalse(response.data['sandbox'])

    @patch('loja.views.criar_preferencia_pagamento')
    @override_settings(MERCADOPAGO_SANDBOX=False, MERCADOPAGO_PUBLIC_KEY='APP_USR_PUBLIC')
    def test_producao_usa_init_point_mesmo_com_url_sandbox(self, mock_criar):
        live = 'https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=pref-live'
        sandbox = 'https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=pref-live'
        mock_criar.return_value = {
            'preference_id': 'pref-live',
            'init_point': live,
            'sandbox_init_point': sandbox,
            'checkout_url': sandbox,
        }

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['checkout_url'], live)
        self.assertFalse(response.data['sandbox'])

    @patch('loja.views.criar_preferencia_pagamento')
    @override_settings(MERCADOPAGO_SANDBOX=True, MERCADOPAGO_PUBLIC_KEY='TEST_PUBLIC_KEY')
    def test_sandbox_usa_url_de_teste(self, mock_criar):
        live = 'https://www.mercadopago.com.br/checkout/v1/redirect?pref_id=pref-test'
        sandbox = 'https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=pref-test'
        mock_criar.return_value = {
            'preference_id': 'pref-test',
            'init_point': live,
            'sandbox_init_point': sandbox,
        }

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['checkout_url'], sandbox)
        self.assertTrue(response.data['sandbox'])


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

    def test_init_gestor_sem_login(self):
        response = self.client.get(reverse('assistant_init'), {'audience': 'gestor'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('greeting', response.json())

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
            **ENDERECO_TESTE,
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.produto,
            quantidade=1,
            preco_unitario=self.produto.preco,
        )
        self.client.force_login(self.user)

    def test_checkout_mostra_somente_pix(self):
        response = self.client.get(reverse('checkout', kwargs={'pedido_id': self.pedido.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pagar com Pix')
        self.assertContains(response, '/api/pedidos/${pedidoId}/pix/')
        self.assertNotContains(response, 'payment-brick-container')
        self.assertNotContains(response, 'sdk.mercadopago.com')


class GerarPixViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='pixer', password='senha123', email='pixer@example.com',
        )
        self.client.force_authenticate(user=self.user)
        self.produto = Produto.objects.create(
            titulo='Filme Pix', preco=Decimal('20.00'), estoque=5,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user, valor_total=Decimal('20.00'), **ENDERECO_TESTE,
        )
        ItemPedido.objects.create(
            pedido=self.pedido, produto=self.produto, quantidade=1, preco_unitario=Decimal('20.00'),
        )
        self.url = reverse('gerar_pix', kwargs={'pedido_id': self.pedido.pk})

    @patch('loja.views.gerar_pix')
    def test_dvd_sem_endereco_nao_gera_pix(self, mock_pix):
        Pedido.objects.filter(pk=self.pedido.pk).update(entrega_cep='')
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('endereço', response.data['detail'])
        mock_pix.assert_not_called()

    @patch('loja.views.gerar_pix')
    def test_devolve_qr_code(self, mock_pix):
        mock_pix.return_value = {
            'id': 777,
            'status': 'pending',
            'date_of_expiration': '2026-10-06T12:30:00.000-03:00',
            'point_of_interaction': {
                'transaction_data': {
                    'qr_code': '00020126pix',
                    'qr_code_base64': 'base64img',
                    'ticket_url': 'https://mp.example/ticket',
                }
            },
        }
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['pix']['qr_code'], '00020126pix')
        self.assertEqual(response.data['pix']['qr_code_base64'], 'base64img')
        self.assertEqual(response.data['payment_id'], '777')

    @patch('loja.views.gerar_pix')
    def test_salva_email_quando_usuario_nao_tem(self, mock_pix):
        self.user.email = ''
        self.user.save()
        mock_pix.return_value = {
            'id': 1, 'status': 'pending',
            'point_of_interaction': {'transaction_data': {'qr_code': 'x', 'qr_code_base64': 'y'}},
        }
        response = self.client.post(self.url, {'email': 'novo@example.com'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'novo@example.com')

    def test_pedido_de_outro_cliente(self):
        outro = User.objects.create_user(username='outro', password='senha123')
        self.client.force_authenticate(user=outro)
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 404)

    @patch('loja.views.gerar_pix')
    def test_pedido_aprovado_nao_gera_novo_pix(self, mock_pix):
        self.pedido.status = Pedido.STATUS_APROVADO
        self.pedido.save()
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], Pedido.STATUS_APROVADO)
        mock_pix.assert_not_called()


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
    def test_recusa_cartao(self, mock_criar):
        response = self.client.post(self.url, {
            'token': 'tok_test',
            'payment_method_id': 'master',
            'installments': 1,
            'payer': {'email': 'comprador@example.com'},
        }, format='json')
        self.assertEqual(response.status_code, 400)
        mock_criar.assert_not_called()

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


class GestaoPainelTests(TestCase):
    def setUp(self):
        self.gestor = User.objects.create_user(
            username='gestor_painel', password='senha', is_staff=True, first_name='Mateus',
        )
        self.cliente = User.objects.create_user(
            username='cliente_painel', password='senha', email='cliente_painel@example.com',
        )
        self.disco = Musica.objects.create(
            titulo='Abbey Road', artista='Beatles', preco=Decimal('40.00'),
            estoque=1, disponivel_venda=True, ativo=True,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.cliente,
            status=Pedido.STATUS_APROVADO,
            valor_total=Decimal('40.00'),
        )
        ItemPedido.objects.create(
            pedido=self.pedido,
            produto=self.disco,
            modalidade='venda',
            quantidade=2,
            preco_unitario=Decimal('40.00'),
        )

    def test_anonimo_abre_o_painel(self):
        response = self.client.get(reverse('gestao_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_entrar_vai_para_o_painel(self):
        response = self.client.get(reverse('gestao_entrar'))
        self.assertRedirects(response, reverse('gestao_dashboard'))

    def test_cliente_comum_abre_o_estoque(self):
        self.client.force_login(self.cliente)
        response = self.client.get(reverse('gestao_estoque'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_mostra_venda_real(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse('gestao_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Abbey Road')
        self.assertContains(response, 'Mateus')
        self.assertContains(response, '40')

    def test_sem_historico_nao_inventa_percentual(self):
        from loja.painel_gestao import cards_dashboard

        cards = cards_dashboard()
        self.assertIsNone(cards['faturamento_var'])
        self.assertEqual(cards['vendas_mes'], 2)

    def test_periodo_vazio_avisa(self):
        self.pedido.status = Pedido.STATUS_CANCELADO
        self.pedido.save(update_fields=['status'])
        self.client.force_login(self.gestor)
        response = self.client.get(reverse('gestao_dashboard') + '?periodo=7')
        self.assertContains(response, 'Ainda não existem dados suficientes para este período.')

    def test_ontem_nao_herda_venda_de_hoje(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse('gestao_dashboard') + '?periodo=ontem')
        self.assertContains(response, 'Ainda não existem dados suficientes para este período.')
        self.assertContains(response, 'Resumo de hoje')
        self.assertContains(response, 'Precisa da sua atenção')

    def test_gestor_redefine_senha_sem_expor_a_antiga(self):
        self.client.force_login(self.gestor)
        url = reverse('gestao_cliente_detalhe', kwargs={'pk': self.cliente.pk})
        response = self.client.get(url)
        self.assertContains(response, self.cliente.username)
        self.assertNotContains(response, 'senha123')
        response = self.client.post(url, {
            'nova_senha': 'NovaSenha-123',
            'confirmar_senha': 'NovaSenha-123',
        })
        self.assertRedirects(response, url)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.username, 'cliente_painel')
        self.assertTrue(self.cliente.check_password('NovaSenha-123'))
        self.assertFalse(self.cliente.check_password('senha'))

    def test_exclui_cliente_sem_pedido_e_preserva_quem_comprou(self):
        sem_pedido = User.objects.create_user(username='so_cadastro', password='senha')
        self.client.force_login(self.gestor)
        url = reverse('gestao_clientes_excluir')
        resposta = self.client.post(url, {'ids': [sem_pedido.pk, self.cliente.pk]})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'so_cadastro')
        self.assertContains(resposta, 'tem pedido')
        self.client.post(url, {
            'acao': 'excluir',
            'ids': [sem_pedido.pk, self.cliente.pk],
        })
        self.assertFalse(User.objects.filter(pk=sem_pedido.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.cliente.pk).exists())

    def test_resumo_de_hoje_conta_a_venda(self):
        from loja.painel_gestao import resumo_hoje

        hoje = resumo_hoje()
        self.assertEqual(hoje['vendas'], 2)
        self.assertEqual(hoje['pedidos'], 1)

    def test_relatorio_csv_so_para_gestor(self):
        self.client.force_login(self.gestor)
        response = self.client.get(reverse('gestao_relatorios') + '?export=csv')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('Abbey Road', response.content.decode('utf-8'))

    def test_arquivo_grande_nao_e_enviado_para_a_nuvem(self):
        from loja.storage import LIMITE_ARQUIVO_NUVEM, SupabaseStorage

        class ArquivoGrande:
            size = LIMITE_ARQUIVO_NUVEM + 1

            def read(self):
                raise AssertionError('o arquivo grande não pode ser lido inteiro')

            def seek(self, pos):
                return None

        with self.assertRaises(RuntimeError) as ctx:
            SupabaseStorage()._save('filme.mkv', ArquivoGrande())
        self.assertIn('arquivo-grande', str(ctx.exception))

    @override_settings(DEBUG=True)
    def test_nova_midia_salva_capa_e_arquivo_no_computador(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        quadro = io.BytesIO()
        Image.new('RGB', (8, 8), 'red').save(quadro, 'PNG')
        capa = SimpleUploadedFile('capa-cinema.png', quadro.getvalue(), content_type='image/png')
        filme = SimpleUploadedFile('poderoso-chefao.mkv', b'\x1aE\xdf\xa3filme', content_type='video/x-matroska')

        pagina = self.client.get(reverse('gestao_midia_criar'))
        self.assertContains(pagina, 'A capa fica salva neste computador')
        self.assertNotContains(pagina, 'CLOUDINARY_URL')

        resposta = self.client.post(reverse('gestao_midia_criar'), {
            'titulo': 'O Poderoso Chefao',
            'tipo': 'dvd',
            'diretor': 'Francis Ford Coppola',
            'ano': '1972',
            'duracao_min': '175',
            'descricao': 'Sinopse',
            'preco': '40.00',
            'estoque': '1',
            'preco_aluguel': '0',
            'dias_aluguel': '7',
            'estoque_aluguel': '0',
            'disponivel_venda': 'on',
            'ativo': 'on',
            'imagem': capa,
            'arquivo': filme,
        })
        self.assertEqual(resposta.status_code, 302)
        midia = MidiaAudiovisual.objects.get(titulo='O Poderoso Chefao')
        self.assertTrue(midia.imagem.name.endswith('capa-cinema.png'))
        self.assertTrue(midia.arquivo.name.endswith('poderoso-chefao.mkv'))
        self.assertTrue(midia.imagem.storage.exists(midia.imagem.name))
        self.assertTrue(midia.arquivo.storage.exists(midia.arquivo.name))

    def test_filme_online_exige_preco_e_link(self):
        resposta = self.client.post(reverse('gestao_midia_criar'), {
            'titulo': 'Sem Link',
            'tipo': 'filme',
            'disponivel_assistir': 'on',
            'preco_assistir': '',
            'ativo': 'on',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Informe quanto custa para assistir online.')
        self.assertContains(resposta, 'Coloque o link do filme completo')

        resposta = self.client.post(reverse('gestao_midia_criar'), {
            'titulo': 'Com Link',
            'tipo': 'filme',
            'disponivel_assistir': 'on',
            'preco_assistir': '9.90',
            'filme_url': 'https://youtu.be/abcdefghijk',
            'disponivel_venda': 'on',
            'preco': '35.00',
            'estoque': '3',
            'ativo': 'on',
        })
        self.assertEqual(resposta.status_code, 302)
        filme = MidiaAudiovisual.objects.get(titulo='Com Link')
        self.assertTrue(filme.pode_assistir)
        self.assertTrue(filme.pode_comprar)
        self.assertEqual(filme.preco_assistir, Decimal('9.90'))

    def test_aceita_codigo_incorporar_do_bunny(self):
        video = '0f6a7c1e-2b3d-4e5f-8a9b-0c1d2e3f4a5b'
        codigo = (
            '<div style="position:relative;padding-top:56.25%;">'
            f'<iframe src="https://iframe.mediadelivery.net/embed/123456/{video}'
            '?autoplay=true&amp;loop=false&amp;muted=true&amp;preload=true&amp;responsive=true" '
            'loading="lazy" style="border:0;position:absolute;top:0;height:100%;width:100%;" '
            'allow="accelerometer;gyroscope;autoplay;encrypted-media;picture-in-picture;" '
            'allowfullscreen="true"></iframe></div>'
        )
        resposta = self.client.post(reverse('gestao_midia_criar'), {
            'titulo': 'Nosferatu',
            'tipo': 'filme',
            'disponivel_assistir': 'on',
            'preco_assistir': '5.00',
            'filme_url': codigo,
            'ativo': 'on',
        })
        self.assertEqual(resposta.status_code, 302)
        filme = MidiaAudiovisual.objects.get(titulo='Nosferatu')
        self.assertTrue(filme.filme_url.startswith(f'https://iframe.mediadelivery.net/embed/123456/{video}'))
        self.assertEqual(filme.filme_embed_url, f'https://iframe.mediadelivery.net/embed/123456/{video}')


class PixDaLojaTests(TestCase):
    def setUp(self):
        from .models import ConfiguracaoPix

        self.config = ConfiguracaoPix.objects.create(
            tipo_chave='email', chave='Loja@Exemplo.com',
            nome_recebedor='Mateus Pereira', cidade='Belo Horizonte',
        )
        self.user = User.objects.create_user(username='comprador_pix', password='senha')
        self.filme = MidiaAudiovisual.objects.create(
            titulo='Filme Pix', ativo=True, disponivel_assistir=True, preco=Decimal('0'),
            preco_assistir=Decimal('20.20'), filme_url='https://youtu.be/abcdefghijk',
        )
        self.pedido = Pedido.objects.create(cliente=self.user, valor_total=Decimal('20.20'))
        ItemPedido.objects.create(
            pedido=self.pedido, produto=self.filme, modalidade='assistir',
            quantidade=1, preco_unitario=Decimal('20.20'),
        )

    def test_codigo_segue_o_exemplo_do_banco_central(self):
        from .pix import montar_copia_e_cola

        self.assertEqual(
            montar_copia_e_cola('123e4567-e12b-12d1-a456-426655440000', 'Fulano de Tal', 'BRASILIA'),
            '00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000'
            '5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***63041D3D',
        )

    @patch('loja.views.gerar_pix')
    def test_checkout_gera_qr_e_copia_e_cola_com_a_chave_da_loja(self, mock_mp):
        api = APIClient()
        api.force_authenticate(user=self.user)
        resposta = api.post(reverse('gerar_pix', kwargs={'pedido_id': self.pedido.pk}), {}, format='json')
        self.assertEqual(resposta.status_code, 200)
        mock_mp.assert_not_called()
        codigo = resposta.data['pix']['qr_code']
        self.assertIn('loja@exemplo.com', codigo)
        self.assertIn('540520.20', codigo)
        self.assertIn('Mateus Pereira', codigo)
        self.assertIn('VP%d' % self.pedido.pk, codigo)
        self.assertTrue(resposta.data['pix']['qr_code_base64'])
        self.assertTrue(resposta.data['manual'])

    def test_cliente_avisa_e_gestao_confirma(self):
        api = APIClient()
        api.force_authenticate(user=self.user)
        api.post(reverse('informar_pix_pago', kwargs={'pedido_id': self.pedido.pk}))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.STATUS_EM_ANALISE)

        resposta = self.client.post(
            reverse('gestao_pedido_pagamento', kwargs={'pk': self.pedido.pk}), {'acao': 'aprovar'},
        )
        self.assertRedirects(resposta, reverse('gestao_pedido_detalhe', kwargs={'pk': self.pedido.pk}))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.STATUS_APROVADO)
        self.assertTrue(self.pedido.itens.get().acesso_liberado)

    def test_gestao_salva_chave_e_mostra_qr_de_teste(self):
        resposta = self.client.post(reverse('gestao_configuracao_pix'), {
            'tipo_chave': 'cpf', 'chave': '123', 'nome_recebedor': 'Mateus', 'cidade': 'BH',
        })
        self.assertContains(resposta, 'O CPF tem 11 números.')
        self.client.post(reverse('gestao_configuracao_pix'), {
            'tipo_chave': 'cpf', 'chave': '123.456.789-09', 'nome_recebedor': 'Mateus', 'cidade': 'BH',
        })
        pagina = self.client.get(reverse('gestao_configuracao_pix'))
        self.assertContains(pagina, 'QR Code de teste')
        self.assertContains(pagina, '0111' + '12345678909')


class AcompanharEntregaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='espera_dvd', password='senha', email='dvd@example.com')
        self.client.force_login(self.user)
        self.filme = MidiaAudiovisual.objects.create(
            titulo='Os Canhões de Navarone', ativo=True,
            disponivel_venda=True, preco=Decimal('20.20'), estoque=3,
        )
        self.pedido = Pedido.objects.create(
            cliente=self.user, valor_total=Decimal('20.20'),
            status=Pedido.STATUS_EM_ANALISE, **ENDERECO_TESTE,
        )
        ItemPedido.objects.create(
            pedido=self.pedido, produto=self.filme, modalidade='venda',
            quantidade=1, preco_unitario=Decimal('20.20'),
        )
        self.url = reverse('pedido_acompanhar', kwargs={'pedido_id': self.pedido.pk})

    def test_linha_do_tempo_acompanha_cada_etapa(self):
        from django.core import mail

        pagina = self.client.get(self.url)
        self.assertContains(pagina, 'Pedido feito')
        self.assertContains(pagina, 'Saiu para entrega')

        self.client.post(
            reverse('gestao_pedido_pagamento', kwargs={'pk': self.pedido.pk}), {'acao': 'aprovar'},
        )
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status_entrega, 'preparando')

        self.client.post(reverse('gestao_pedido_entrega', kwargs={'pk': self.pedido.pk}), {
            'status_entrega': 'enviado', 'transportadora': 'Correios',
            'codigo_rastreio': 'aa123456789br', 'mensagem': 'Chega em até 5 dias úteis',
        })
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.codigo_rastreio, 'AA123456789BR')
        self.assertTrue(any('Enviado' in m.subject for m in mail.outbox))

        pagina = self.client.get(self.url)
        self.assertContains(pagina, '<h1>Enviado</h1>', html=True)
        self.assertContains(pagina, 'AA123456789BR')
        self.assertContains(pagina, 'Chega em até 5 dias úteis')
        self.assertContains(pagina, 'rastreamento.correios.com.br')
        etapas = {e['chave']: e for e in self.pedido.linha_do_tempo()}
        self.assertTrue(etapas['enviado']['atual'])
        self.assertFalse(etapas['entregue']['feita'])

        lista = self.client.get(reverse('meus_pedidos'))
        self.assertContains(lista, 'Acompanhar entrega')

    def test_outro_cliente_nao_ve_o_pedido(self):
        outro = User.objects.create_user(username='curioso', password='senha')
        self.client.force_login(outro)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_entrega_so_depois_do_pagamento(self):
        self.client.post(reverse('gestao_pedido_entrega', kwargs={'pk': self.pedido.pk}), {
            'status_entrega': 'enviado',
        })
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status_entrega, '')


class BunnyStreamTests(TestCase):
    VIDEO = '3f2a9c1e-1111-4222-8333-944455556666'

    def test_link_play_vira_player_embed(self):
        from .models import embed_de_video

        self.assertEqual(
            embed_de_video(f'https://iframe.mediadelivery.net/play/123456/{self.VIDEO}'),
            f'https://iframe.mediadelivery.net/embed/123456/{self.VIDEO}',
        )

    @override_settings(BUNNY_STREAM_TOKEN_KEY='chave-teste')
    def test_player_do_cliente_sai_assinado(self):
        import hashlib
        import re

        from .models import assinar_embed_bunny

        url = assinar_embed_bunny(f'https://iframe.mediadelivery.net/embed/123456/{self.VIDEO}')
        partes = re.search(r'\?token=([0-9a-f]{64})&expires=(\d+)$', url)
        self.assertIsNotNone(partes)
        esperado = hashlib.sha256(f'chave-teste{self.VIDEO}{partes.group(2)}'.encode()).hexdigest()
        self.assertEqual(partes.group(1), esperado)

    def test_sem_chave_o_link_fica_igual(self):
        from .models import assinar_embed_bunny

        url = f'https://iframe.mediadelivery.net/embed/123456/{self.VIDEO}'
        self.assertEqual(assinar_embed_bunny(url), url)


class RegistroClienteTests(TestCase):
    def test_senha_fraca_mostra_todas_as_regras(self):
        resposta = self.client.post(reverse('registrar'), {
            'username': 'mateus', 'email': '0125mateus@gmail.com',
            'password1': '123', 'password2': '123',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'pelo menos 8 caracteres')
        self.assertContains(resposta, 'inteiramente numérica')
        self.assertFalse(User.objects.exists())

    def test_cadastro_com_senha_boa_entra_na_loja(self):
        resposta = self.client.post(reverse('registrar'), {
            'username': 'mateus', 'email': '0125mateus@gmail.com',
            'password1': 'Cinema-2026', 'password2': 'Cinema-2026',
        })
        self.assertRedirects(resposta, reverse('home'))
        self.assertTrue(User.objects.filter(username='mateus').exists())


class FilmesAssistirEDvdTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cinefilo', password='senha', email='c@example.com')
        self.client.force_login(self.user)
        self.filme = MidiaAudiovisual.objects.create(
            titulo='A Ponte do Rio Kwai', tipo='filme', ativo=True,
            disponivel_assistir=True, preco_assistir=Decimal('9.90'),
            filme_url='https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view?usp=sharing',
            disponivel_venda=True, preco=Decimal('39.90'), estoque=2,
        )

    def _adicionar(self, modalidade):
        return self.client.post(
            reverse('adicionar_carrinho', kwargs={'produto_id': self.filme.pk}),
            {'modalidade': modalidade},
        )

    def test_pagina_do_filme_mostra_as_duas_opcoes(self):
        resposta = self.client.get(reverse('produto_detalhe', kwargs={'produto_id': self.filme.pk}))
        self.assertContains(resposta, 'Assistir online')
        self.assertContains(resposta, 'R$ 9,90')
        self.assertContains(resposta, 'DVD físico')
        self.assertContains(resposta, 'R$ 39,90')
        self.assertNotContains(resposta, 'Alugar')

    def test_sem_link_nao_vende_assistir_online(self):
        self.filme.filme_url = ''
        self.filme.save()
        resposta = self.client.get(reverse('produto_detalhe', kwargs={'produto_id': self.filme.pk}))
        self.assertNotContains(resposta, 'R$ 9,90')
        self.assertContains(resposta, 'DVD físico')
        self._adicionar('assistir')
        self.assertFalse(self.client.session.get('carrinho'))
        catalogo = self.client.get(reverse('catalogo_filmes'), {'modalidade': 'assistir'})
        self.assertEqual(catalogo.context['total'], 0)

    def test_assistir_online_vai_direto_para_o_pix(self):
        self._adicionar('assistir')
        self._adicionar('assistir')
        resposta = self.client.post(reverse('finalizar_pedido'))
        pedido = Pedido.objects.get(cliente=self.user)
        self.assertRedirects(resposta, reverse('checkout', kwargs={'pedido_id': pedido.pk}))
        item = pedido.itens.get()
        self.assertEqual(item.modalidade, 'assistir')
        self.assertEqual(item.quantidade, 1)
        self.assertEqual(pedido.valor_total, Decimal('9.90'))
        self.filme.refresh_from_db()
        self.assertEqual(self.filme.estoque, 2)

    def test_dvd_pede_endereco_antes_do_pix(self):
        self._adicionar('venda')
        resposta = self.client.post(reverse('finalizar_pedido'))
        pedido = Pedido.objects.get(cliente=self.user)
        url_entrega = reverse('pedido_entrega', kwargs={'pedido_id': pedido.pk})
        url_checkout = reverse('checkout', kwargs={'pedido_id': pedido.pk})
        self.assertRedirects(resposta, url_entrega)
        self.assertRedirects(self.client.get(url_checkout), url_entrega)

        resposta = self.client.post(url_entrega, {**ENDERECO_TESTE, 'entrega_cep': '01310100'})
        self.assertRedirects(resposta, url_checkout)
        pedido.refresh_from_db()
        self.assertEqual(pedido.entrega_cep, '01310-100')
        self.assertTrue(pedido.tem_endereco)
        self.assertContains(self.client.get(url_checkout), 'Avenida Paulista')
        self.filme.refresh_from_db()
        self.assertEqual(self.filme.estoque, 1)

    def test_endereco_incompleto_nao_avanca(self):
        self._adicionar('venda')
        self.client.post(reverse('finalizar_pedido'))
        pedido = Pedido.objects.get(cliente=self.user)
        resposta = self.client.post(
            reverse('pedido_entrega', kwargs={'pedido_id': pedido.pk}),
            {**ENDERECO_TESTE, 'entrega_cep': '123', 'entrega_numero': ''},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'O CEP tem 8 números.')

    def test_aluguel_nao_entra_no_carrinho(self):
        self.filme.disponivel_aluguel = True
        self.filme.preco_aluguel = Decimal('5.00')
        self.filme.estoque_aluguel = 3
        self.filme.save()
        self._adicionar('aluguel')
        carrinho = self.client.session.get('carrinho', {})
        self.assertNotIn(f'{self.filme.pk}:aluguel', carrinho)

    def test_quem_pagou_assiste_pelo_link_e_dvd_nao_libera(self):
        pedido = Pedido.objects.create(
            cliente=self.user, valor_total=Decimal('49.80'),
            status=Pedido.STATUS_APROVADO, **ENDERECO_TESTE,
        )
        assistir = ItemPedido.objects.create(
            pedido=pedido, produto=self.filme, modalidade='assistir',
            quantidade=1, preco_unitario=Decimal('9.90'),
        )
        dvd = ItemPedido.objects.create(
            pedido=pedido, produto=self.filme, modalidade='venda',
            quantidade=1, preco_unitario=Decimal('39.90'),
        )
        self.assertTrue(assistir.acesso_liberado)
        self.assertFalse(dvd.acesso_liberado)

        resposta = self.client.get(reverse('reproduzir_conteudo', kwargs={'item_id': assistir.pk}))
        self.assertContains(resposta, 'https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/preview')
        self.assertEqual(
            self.client.get(reverse('reproduzir_conteudo', kwargs={'item_id': dvd.pk})).status_code,
            404,
        )

        biblioteca = self.client.get(reverse('biblioteca'))
        self.assertContains(biblioteca, '▶ Assistir')

    def test_discos_e_livros_saem_da_loja(self):
        self.assertRedirects(self.client.get(reverse('catalogo_discos')), reverse('catalogo_filmes'))
        self.assertRedirects(self.client.get(reverse('catalogo_livros')), reverse('catalogo_filmes'))
        home = self.client.get(reverse('home'))
        self.assertNotContains(home, 'Vinis em destaque')
        self.assertContains(home, 'A Ponte do Rio Kwai')
