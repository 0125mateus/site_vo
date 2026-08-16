from django.urls import path

from . import views
from . import views_assistant

urlpatterns = [
    path(
        'pedidos/<int:pedido_id>/pagamento/',
        views.CriarPreferenciaPagamentoView.as_view(),
        name='criar_preferencia_pagamento',
    ),
    path(
        'pedidos/<int:pedido_id>/status/',
        views.PedidoStatusView.as_view(),
        name='pedido_status',
    ),
    path(
        'webhooks/mercadopago/',
        views.MercadoPagoWebhookView.as_view(),
        name='mercadopago_webhook',
    ),
    path('assistente/init/', views_assistant.assistant_init, name='assistant_init'),
    path('assistente/chat/', views_assistant.assistant_chat_view, name='assistant_chat'),
    # aliases (JS antigo / cache)
    path('assistant/init/', views_assistant.assistant_init),
    path('assistant/chat/', views_assistant.assistant_chat_view),
]
