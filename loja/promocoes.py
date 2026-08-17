from decimal import Decimal

from django.utils import timezone

from .models import AssinaturaClube, Livro, ModalidadeComercial, Musica, PlanoClube

COMBO_DESCONTO_PERCENT = Decimal('10')


def usuario_tem_clube_ativo(user) -> bool:
    if not user.is_authenticated:
        return False
    return AssinaturaClube.objects.filter(
        usuario=user,
        status=AssinaturaClube.STATUS_ATIVA,
        valido_ate__gte=timezone.localdate(),
    ).exists()


def _assinatura_ativa(user):
    if not user.is_authenticated:
        return None
    return (
        AssinaturaClube.objects.filter(
            usuario=user,
            status=AssinaturaClube.STATUS_ATIVA,
            valido_ate__gte=timezone.localdate(),
        )
        .select_related('plano')
        .first()
    )


def _eh_musica(produto_id) -> bool:
    return Musica.objects.filter(pk=produto_id).exists()


def _eh_livro(produto_id) -> bool:
    return Livro.objects.filter(pk=produto_id).exists()


def calcular_promocoes_carrinho(user, itens_produtos):
    """Calcula descontos de combo livro+disco e benefício do clube."""
    desconto_combo = Decimal('0.00')
    desconto_clube = Decimal('0.00')

    musicas_venda = [
        item for item in itens_produtos
        if item['modalidade'] == ModalidadeComercial.VENDA and _eh_musica(item['produto'].pk)
    ]
    livros_venda = [
        item for item in itens_produtos
        if item['modalidade'] == ModalidadeComercial.VENDA and _eh_livro(item['produto'].pk)
    ]

    if musicas_venda and livros_venda:
        disco = min(musicas_venda, key=lambda x: x['preco_unitario'])
        livro = min(livros_venda, key=lambda x: x['preco_unitario'])
        base = disco['preco_unitario'] + livro['preco_unitario']
        desconto_combo = (base * COMBO_DESCONTO_PERCENT / Decimal('100')).quantize(Decimal('0.01'))

    subtotal_produtos = sum(item['subtotal'] for item in itens_produtos)

    assinatura = _assinatura_ativa(user)
    if assinatura and subtotal_produtos > 0:
        pct = Decimal(assinatura.plano.desconto_extra_percent)
        desconto_clube = (subtotal_produtos * pct / Decimal('100')).quantize(Decimal('0.01'))

    desconto_total = min(subtotal_produtos, desconto_combo + desconto_clube)

    return {
        'desconto_combo': desconto_combo,
        'desconto_clube': desconto_clube,
        'desconto_total': desconto_total,
        'subtotal_produtos': subtotal_produtos,
        'tem_combo': desconto_combo > 0,
        'tem_clube_desconto': desconto_clube > 0,
        'clube_ativo': assinatura is not None,
        'clube_plano': assinatura.plano if assinatura else None,
        'combo_disponivel': bool(musicas_venda and livros_venda),
        'falta_combo_livro': bool(musicas_venda and not livros_venda),
        'falta_combo_disco': bool(livros_venda and not musicas_venda),
    }


def ativar_assinatura_clube(pedido):
    """Estende ou cria assinatura após pagamento aprovado de plano do clube."""
    if not pedido.plano_clube_id:
        return None

    from datetime import timedelta

    hoje = timezone.localdate()
    assinatura = AssinaturaClube.objects.filter(
        usuario=pedido.cliente,
        plano_id=pedido.plano_clube_id,
    ).first()

    if assinatura and assinatura.valido_ate >= hoje:
        valido_ate = assinatura.valido_ate + timedelta(days=30)
    else:
        valido_ate = hoje + timedelta(days=30)

    assinatura, _ = AssinaturaClube.objects.update_or_create(
        usuario=pedido.cliente,
        plano_id=pedido.plano_clube_id,
        defaults={
            'status': AssinaturaClube.STATUS_ATIVA,
            'valido_ate': valido_ate,
            'ultimo_pedido': pedido,
        },
    )
    return assinatura
