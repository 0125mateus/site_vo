import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def _destinatario_pedido(pedido) -> str | None:
    email = (pedido.cliente.email or '').strip()
    return email or None


def enviar_email_pedido_aprovado(pedido) -> bool:
    """
    Envia confirmação quando o pedido é aprovado.
    Retorna True se o e-mail foi enviado; False se não havia destinatário ou falhou.
    """
    destinatario = _destinatario_pedido(pedido)
    if not destinatario:
        logger.info('Pedido #%s aprovado — cliente sem e-mail; confirmação não enviada.', pedido.pk)
        return False

    pedido = (
        pedido.__class__.objects
        .select_related('cliente')
        .prefetch_related('itens__produto')
        .get(pk=pedido.pk)
    )

    site_url = settings.SITE_URL.rstrip('/')
    context = {
        'pedido': pedido,
        'cliente': pedido.cliente,
        'site_url': site_url,
        'biblioteca_url': f'{site_url}{reverse("biblioteca")}',
        'pedidos_url': f'{site_url}{reverse("meus_pedidos")}',
    }

    subject = render_to_string('emails/pedido_aprovado_subject.txt', context).strip()
    text_body = render_to_string('emails/pedido_aprovado_body.txt', context)
    html_body = render_to_string('emails/pedido_aprovado_body.html', context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )
    message.attach_alternative(html_body, 'text/html')

    try:
        message.send(fail_silently=False)
    except Exception:
        logger.exception('Falha ao enviar e-mail de confirmação do pedido #%s para %s', pedido.pk, destinatario)
        return False

    logger.info('E-mail de confirmação enviado — pedido #%s → %s', pedido.pk, destinatario)
    return True
