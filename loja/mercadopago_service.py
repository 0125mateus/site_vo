import hashlib
import hmac
import logging
import uuid
from decimal import Decimal

import mercadopago
from django.conf import settings
from mercadopago.config import RequestOptions

logger = logging.getLogger(__name__)


def get_mercadopago_sdk():
    return mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)


def criar_preferencia_pagamento(pedido):
    sdk = get_mercadopago_sdk()
    site_url = settings.SITE_URL.rstrip('/')

    items = []
    for item in pedido.itens.select_related('produto'):
        titulo = item.produto.titulo
        if item.modalidade == 'aluguel':
            dias = item.dias_aluguel or item.produto.dias_aluguel
            titulo = f'{titulo} (aluguel {dias} dias)'
        items.append({
            'title': titulo,
            'quantity': item.quantidade,
            'unit_price': float(item.preco_unitario),
            'currency_id': 'BRL',
        })

    if pedido.plano_clube_id:
        items.append({
            'title': f'Assinatura — {pedido.plano_clube.titulo}',
            'quantity': 1,
            'unit_price': float(pedido.plano_clube.preco_mensal),
            'currency_id': 'BRL',
        })

    if pedido.desconto > 0 and items:
        bruto = sum(i['unit_price'] * i['quantity'] for i in items)
        if bruto > 0:
            alvo = float(pedido.valor_total)
            fator = alvo / bruto
            for item in items:
                item['unit_price'] = round(item['unit_price'] * fator, 2)
            ajuste = alvo - sum(i['unit_price'] * i['quantity'] for i in items)
            if items:
                items[-1]['unit_price'] = round(items[-1]['unit_price'] + ajuste, 2)

    preference_data = {
        'items': items,
        'back_urls': {
            'success': f'{site_url}/pedidos/{pedido.pk}/processando/',
            'failure': f'{site_url}/pedidos/{pedido.pk}/processando/?result=failure',
            'pending': f'{site_url}/pedidos/{pedido.pk}/processando/?result=pending',
        },
        'auto_return': 'approved',
        'external_reference': str(pedido.pk),
        'notification_url': f'{site_url}/api/webhooks/mercadopago/',
    }

    logger.info('Criando preferência Mercado Pago para pedido %s', pedido.pk)
    response = sdk.preference().create(preference_data)

    if response.get('status') not in (200, 201):
        logger.error(
            'Erro ao criar preferência para pedido %s: status=%s',
            pedido.pk,
            response.get('status'),
        )
        raise MercadoPagoAPIError('Não foi possível iniciar o pagamento. Tente novamente.')

    preference = response['response']
    preference_id = preference.get('id')
    if not preference_id:
        raise MercadoPagoAPIError('Resposta inválida do gateway de pagamento.')

    pedido.mercadopago_preference_id = str(preference_id)
    pedido.save(update_fields=['mercadopago_preference_id'])
    return {
        'preference_id': str(preference_id),
        'init_point': preference.get('init_point') or '',
        'sandbox_init_point': preference.get('sandbox_init_point') or '',
    }


def _json_dict(value):
    if isinstance(value, dict):
        return {str(k): _json_dict(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_dict(v) for v in value]
    return value


def _mensagem_erro_mp(response):
    body = response.get('response') or {}
    if isinstance(body, dict):
        causes = body.get('cause') or []
        if causes and isinstance(causes, list) and isinstance(causes[0], dict):
            desc = causes[0].get('description') or causes[0].get('code')
            if desc:
                return str(desc)
        if body.get('message'):
            return str(body['message'])
    return 'Não foi possível processar o pagamento. Tente novamente.'


def montar_payload_pagamento_brick(pedido, form_data):
    """Monta o body da API de pagamentos sem campos inválidos do Brick."""
    form_data = _json_dict(form_data) if isinstance(form_data, dict) else {}
    method = str(
        form_data.get('payment_method_id') or form_data.get('paymentMethodId') or ''
    ).strip().lower()
    if not method:
        raise MercadoPagoAPIError('Forma de pagamento não informada.')

    raw_payer = form_data.get('payer') if isinstance(form_data.get('payer'), dict) else {}
    email = str(raw_payer.get('email') or getattr(pedido.cliente, 'email', '') or '').strip()
    if not email:
        raise MercadoPagoAPIError('Informe um e-mail para gerar o Pix.')

    payer = {'email': email}
    ident = raw_payer.get('identification')
    if isinstance(ident, dict) and ident.get('type') and ident.get('number'):
        payer['identification'] = {
            'type': str(ident['type']),
            'number': str(ident['number']).replace('.', '').replace('-', ''),
        }
    entity_type = raw_payer.get('entity_type')
    if entity_type in ('individual', 'association'):
        payer['entity_type'] = entity_type
    for key in ('first_name', 'last_name'):
        if raw_payer.get(key):
            payer[key] = raw_payer[key]

    payload = {
        'transaction_amount': float(pedido.valor_total),
        'payment_method_id': method,
        'payer': payer,
        'external_reference': str(pedido.pk),
        'description': f'Pedido #{pedido.pk} — Vinil & Página',
        'notification_url': f"{settings.SITE_URL.rstrip('/')}/api/webhooks/mercadopago/",
    }
    if form_data.get('token'):
        payload['token'] = form_data['token']
    if form_data.get('installments') not in (None, ''):
        payload['installments'] = int(form_data['installments'])
    if form_data.get('issuer_id') not in (None, ''):
        payload['issuer_id'] = form_data['issuer_id']
    return payload


def dados_pix_do_pagamento(payment):
    tx = ((payment or {}).get('point_of_interaction') or {}).get('transaction_data') or {}
    qr_code = tx.get('qr_code')
    if not qr_code:
        return None
    return {
        'qr_code': qr_code,
        'qr_code_base64': tx.get('qr_code_base64') or '',
        'ticket_url': tx.get('ticket_url') or '',
    }


def criar_pagamento_com_brick(pedido, form_data):
    """Cria o pagamento na API do MP a partir do formData do Payment Brick."""
    if not isinstance(form_data, dict) or not form_data:
        raise MercadoPagoAPIError('Dados de pagamento inválidos.')

    sdk = get_mercadopago_sdk()
    payload = montar_payload_pagamento_brick(pedido, form_data)
    options = RequestOptions(custom_headers={'X-Idempotency-Key': str(uuid.uuid4())})

    logger.info('Criando pagamento Brick para pedido %s método=%s', pedido.pk, payload.get('payment_method_id'))
    response = sdk.payment().create(payload, options)
    if response.get('status') not in (200, 201):
        logger.error(
            'Erro ao criar pagamento Brick pedido %s: status=%s body=%s',
            pedido.pk,
            response.get('status'),
            response.get('response'),
        )
        raise MercadoPagoAPIError(_mensagem_erro_mp(response))

    payment = response['response']
    aplicar_pagamento_ao_pedido(pedido, payment)
    return payment


def buscar_pagamento(payment_id):
    sdk = get_mercadopago_sdk()
    response = sdk.payment().get(payment_id)

    if response.get('status') != 200:
        logger.error('Erro ao buscar pagamento %s: status=%s', payment_id, response.get('status'))
        raise MercadoPagoAPIError('Pagamento não encontrado no Mercado Pago.')

    return response['response']


def buscar_pagamentos_por_pedido(pedido):
    """Lista pagamentos no MP associados ao pedido (external_reference)."""
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        return []

    sdk = get_mercadopago_sdk()
    response = sdk.payment().search({
        'external_reference': str(pedido.pk),
        'sort': 'date_created',
        'criteria': 'desc',
    })

    if response.get('status') != 200:
        logger.warning(
            'Busca de pagamentos do pedido %s falhou: status=%s',
            pedido.pk,
            response.get('status'),
        )
        return []

    return response.get('response', {}).get('results', [])


def aplicar_pagamento_ao_pedido(pedido, payment):
    """Atualiza Pagamento e status do Pedido conforme resposta do Mercado Pago."""
    from loja.models import Pagamento

    payment_id = payment.get('id')
    if not payment_id:
        return pedido

    mp_status = payment.get('status', '')
    metodo = payment.get('payment_type_id') or payment.get('payment_method_id')
    valor = Decimal(str(payment.get('transaction_amount', pedido.valor_total)))
    status_anterior = pedido.status

    Pagamento.objects.update_or_create(
        pedido=pedido,
        defaults={
            'mercadopago_payment_id': str(payment_id),
            'status': mp_status,
            'metodo_pagamento': metodo,
            'valor': valor,
        },
    )

    if mp_status == 'approved':
        pedido.status = pedido.STATUS_APROVADO
    elif mp_status in ('pending', 'in_process'):
        pedido.status = pedido.STATUS_EM_ANALISE
    elif mp_status == 'rejected':
        pedido.status = pedido.STATUS_RECUSADO

    pedido.save(update_fields=['status'])
    logger.info('Pedido %s sincronizado com MP — status %s', pedido.pk, pedido.status)

    if status_anterior != pedido.STATUS_APROVADO and pedido.status == pedido.STATUS_APROVADO:
        from loja.email_service import enviar_email_pedido_aprovado
        from loja.promocoes import ativar_assinatura_clube

        enviar_email_pedido_aprovado(pedido)
        ativar_assinatura_clube(pedido)

    return pedido


def sincronizar_pedido_com_mercadopago(pedido):
    """
    Consulta a API do MP quando o webhook ainda não atualizou o pedido.
    Útil em desenvolvimento local sem ngrok.
    """
    if pedido.status not in (pedido.STATUS_AGUARDANDO, pedido.STATUS_EM_ANALISE):
        return pedido

    pagamentos = buscar_pagamentos_por_pedido(pedido)
    if not pagamentos:
        return pedido

    # O mais recente define o status (lista já vem em ordem desc).
    return aplicar_pagamento_ao_pedido(pedido, pagamentos[0])


def validar_assinatura_webhook(request):
    """
    Valida x-signature conforme documentação oficial do Mercado Pago.
    https://www.mercadopago.com.br/developers/en/docs/your-integrations/notifications/webhooks
    """
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secret:
        logger.warning('MERCADOPAGO_WEBHOOK_SECRET não configurado — webhook rejeitado')
        return False

    x_signature = request.headers.get('x-signature', '')
    x_request_id = request.headers.get('x-request-id', '')
    data_id = request.GET.get('data.id') or request.GET.get('id', '')

    if not x_signature or not x_request_id or not data_id:
        logger.error('Webhook sem cabeçalhos ou data.id necessários')
        return False

    parts = {}
    for part in x_signature.split(','):
        key, _, value = part.partition('=')
        parts[key.strip()] = value.strip()

    ts = parts.get('ts')
    received_hash = parts.get('v1')
    if not ts or not received_hash:
        logger.error('Webhook com x-signature malformado')
        return False

    manifest = f'id:{data_id};request-id:{x_request_id};ts:{ts};'
    expected_hash = hmac.new(
        secret.encode('utf-8'),
        manifest.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        logger.error('Assinatura do webhook inválida para data.id=%s', data_id)
        return False

    return True


class MercadoPagoAPIError(Exception):
    pass
