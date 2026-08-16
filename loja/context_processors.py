from django.conf import settings

from .models import ModalidadeComercial


CARRINHO_SESSION_KEY = 'carrinho'


def carrinho_context(request):
    raw = request.session.get(CARRINHO_SESSION_KEY, {})
    if raw and all(isinstance(v, int) for v in raw.values()):
        total_itens = sum(raw.values())
    else:
        total_itens = sum(
            (item.get('quantidade', 0) if isinstance(item, dict) else 0)
            for item in raw.values()
        )
    return {
        'carrinho_total_itens': total_itens,
        'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
        'ModalidadeComercial': ModalidadeComercial,
    }
