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

    favoritos_ids = set()
    if request.user.is_authenticated:
        from .models import Favorito
        favoritos_ids = set(
            Favorito.objects.filter(usuario=request.user).values_list('produto_id', flat=True)
        )

    return {
        'carrinho_total_itens': total_itens,
        'favoritos_ids': favoritos_ids,
        'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
        'ModalidadeComercial': ModalidadeComercial,
        'MEDIA_NA_NUVEM': bool(
            getattr(settings, 'USAR_SUPABASE', False) or getattr(settings, 'CLOUDINARY_URL', '')
        ),
        'ARQUIVOS_NO_COMPUTADOR': settings.DEBUG and not (
            getattr(settings, 'USAR_SUPABASE', False) or getattr(settings, 'CLOUDINARY_URL', '')
        ),
        **_gestao_nav(request),
    }


def _gestao_nav(request):
    if not request.path.startswith('/gestao/'):
        return {}
    from .painel_gestao import PRODUTOS_URLS, alertas_contagem, titulo_pagina

    match = getattr(request, 'resolver_match', None)
    url_name = match.url_name if match else ''
    alertas = alertas_contagem()
    return {
        'gestao_titulo': titulo_pagina(url_name),
        'gestao_alertas': alertas,
        'gestao_alertas_total': alertas['total'],
        'gestao_nav_produtos': url_name in PRODUTOS_URLS,
    }
