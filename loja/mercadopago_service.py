import hashlib
import hmac
import logging
from decimal import Decimal

import mercadopago
from django.conf import settings

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

    pedido.mercadopago_preference_id = preference_id
    pedido.save(update_fields=['mercadopago_preference_id'])
    return preference_id


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
