"""Consultas do painel. Só lê o que já está no banco. Não cria número."""

from datetime import datetime, timedelta
from urllib.parse import quote
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from .gestao_services import ESTOQUE_BAIXO_LIMITE
from .models import ItemPedido, Livro, MidiaAudiovisual, ModalidadeComercial, Musica, Pagamento, Pedido, Produto

User = get_user_model()

PERIODOS = {
    '7': 7,
    '30': 30,
    '90': 90,
    '365': 365,
}

TITULOS = {
    'gestao_dashboard': 'Dashboard',
    'gestao_produtos': 'Produtos',
    'gestao_discos_lista': 'Discos',
    'gestao_disco_criar': 'Novo disco',
    'gestao_disco_editar': 'Editar disco',
    'gestao_disco_excluir': 'Excluir disco',
    'gestao_livros_lista': 'Livros',
    'gestao_livro_criar': 'Novo livro',
    'gestao_livro_editar': 'Editar livro',
    'gestao_livro_excluir': 'Excluir livro',
    'gestao_midias_lista': 'Filmes / DVDs',
    'gestao_midia_criar': 'Nova mídia',
    'gestao_midia_editar': 'Editar mídia',
    'gestao_midia_excluir': 'Excluir mídia',
    'gestao_pedidos_lista': 'Pedidos',
    'gestao_pedido_detalhe': 'Pedido',
    'gestao_clientes': 'Clientes',
    'gestao_clientes_excluir': 'Excluir clientes',
    'gestao_cliente_detalhe': 'Cliente',
    'gestao_estoque': 'Estoque',
    'gestao_alugueis': 'Aluguéis',
    'gestao_relatorios': 'Relatórios',
    'gestao_assistente_frases': 'Assistente',
    'gestao_configuracoes': 'Configurações',
    'gestao_planos_clube_lista': 'Clube',
    'gestao_plano_clube_criar': 'Novo plano',
    'gestao_plano_clube_editar': 'Editar plano',
    'gestao_importar_catalogo': 'Importar CSV',
    'gestao_busca': 'Busca',
}

PRODUTOS_URLS = {
    'gestao_produtos',
    'gestao_discos_lista',
    'gestao_disco_criar',
    'gestao_disco_editar',
    'gestao_disco_excluir',
    'gestao_livros_lista',
    'gestao_livro_criar',
    'gestao_livro_editar',
    'gestao_livro_excluir',
    'gestao_midias_lista',
    'gestao_midia_criar',
    'gestao_midia_editar',
    'gestao_midia_excluir',
    'gestao_importar_catalogo',
}


def titulo_pagina(url_name: str) -> str:
    return TITULOS.get(url_name or '', 'Gestão')


def _dinheiro(valor) -> Decimal:
    if valor is None:
        return Decimal('0.00')
    return Decimal(valor).quantize(Decimal('0.01'))


def _variacao(atual, anterior):
    """Percentual só quando o período anterior tem valor. Sem histórico, devolve None."""
    anterior = _dinheiro(anterior)
    if anterior <= 0:
        return None
    atual = _dinheiro(atual)
    return round(float((atual - anterior) / anterior * 100), 1)


def _inicio_mes(dia):
    return dia.replace(day=1)


def _mes_anterior(dia):
    primeiro = _inicio_mes(dia)
    fim = primeiro - timedelta(days=1)
    return _inicio_mes(fim), fim


def faturamento_entre(inicio, fim):
    return Pedido.objects.filter(
        status=Pedido.STATUS_APROVADO,
        criado_em__date__gte=inicio,
        criado_em__date__lte=fim,
    ).aggregate(total=Sum('valor_total'), n=Count('id'), ticket=Avg('valor_total'))


def unidades(modalidade, inicio=None, fim=None):
    qs = ItemPedido.objects.filter(
        pedido__status=Pedido.STATUS_APROVADO,
        modalidade=modalidade,
    )
    if inicio:
        qs = qs.filter(pedido__criado_em__date__gte=inicio)
    if fim:
        qs = qs.filter(pedido__criado_em__date__lte=fim)
    return qs.aggregate(qtd=Sum('quantidade'))['qtd'] or 0


def alertas_contagem():
    hoje = timezone.localdate()
    estoque = Produto.objects.filter(ativo=True).filter(
        Q(disponivel_venda=True, estoque__gt=0, estoque__lte=ESTOQUE_BAIXO_LIMITE)
        | Q(disponivel_aluguel=True, estoque_aluguel__gt=0, estoque_aluguel__lte=ESTOQUE_BAIXO_LIMITE)
    ).distinct().count()
    sem_estoque = Produto.objects.filter(ativo=True, estoque=0, estoque_aluguel=0).count()
    atrasados = ItemPedido.objects.filter(
        modalidade=ModalidadeComercial.ALUGUEL,
        pedido__status=Pedido.STATUS_APROVADO,
        data_devolucao__lt=hoje,
    ).count()
    vencendo = ItemPedido.objects.filter(
        modalidade=ModalidadeComercial.ALUGUEL,
        pedido__status=Pedido.STATUS_APROVADO,
        data_devolucao__gte=hoje,
        data_devolucao__lte=hoje + timedelta(days=3),
    ).count()
    aguardando = Pedido.objects.filter(status=Pedido.STATUS_AGUARDANDO).count()
    em_analise = Pedido.objects.filter(status=Pedido.STATUS_EM_ANALISE).count()
    tipos = [estoque, sem_estoque, atrasados, vencendo, aguardando, em_analise]
    return {
        'estoque_baixo': estoque,
        'sem_estoque': sem_estoque,
        'alugueis_atrasados': atrasados,
        'alugueis_vencendo': vencendo,
        'pedidos_aguardando': aguardando,
        'pedidos_analise': em_analise,
        'pedidos_pendentes': aguardando + em_analise,
        'total': sum(1 for valor in tipos if valor),
    }


def serie_faturamento(dias: int):
    hoje = timezone.localdate()
    return serie_entre(hoje - timedelta(days=dias - 1), hoje)


def _dia(valor):
    if hasattr(valor, 'date') and not hasattr(valor, 'hour'):
        return valor
    if hasattr(valor, 'date'):
        return valor.date()
    return valor


def _mapa_por_dia(qs, inicio, fim, campo, agregacao):
    rows = (
        qs.filter(**{f'{campo}__date__gte': inicio, f'{campo}__date__lte': fim})
        .annotate(dia=TruncDate(campo))
        .values('dia')
        .annotate(total=agregacao)
    )
    mapa = {}
    for row in rows:
        mapa[_dia(row['dia'])] = row['total'] or 0
    return mapa


def _pontos_periodo(mapa, inicio, fim):
    bruto = []
    cursor = inicio
    while cursor <= fim:
        bruto.append((cursor, mapa.get(cursor, 0)))
        cursor += timedelta(days=1)
    dias = (fim - inicio).days + 1
    if dias <= 31:
        return [{'label': dia.strftime('%d/%m'), 'tick': dia.strftime('%d/%m'), 'total': total} for dia, total in bruto]
    if dias <= 100:
        return _agrupar(bruto, lambda dia: dia.strftime('%d/%m'), 7)
    return _agrupar(bruto, lambda dia: dia.strftime('%m/%Y'), 31)


def _grafico(pontos, escala=None):
    quantidade = len(pontos)
    maior = max((Decimal(str(ponto['total'] or 0)) for ponto in pontos), default=Decimal('0'))
    if escala is None:
        escala = maior if maior > 0 else Decimal('1')
    largura = 8 if quantidade <= 1 else max(3, min(16, (300 / quantidade) - 3))
    passo = 1 if quantidade <= 8 else max(1, quantidade // 6)
    coords = []
    for indice, ponto in enumerate(pontos):
        valor = Decimal(str(ponto['total'] or 0))
        centro = 12 if quantidade <= 1 else 12 + (indice / (quantidade - 1)) * 296
        altura = float(valor / escala) * 88 if escala else 0
        ponto['cx'] = round(centro, 1)
        ponto['x'] = round(centro - largura / 2, 1)
        ponto['h'] = round(altura, 1)
        ponto['y'] = round(108 - altura, 1)
        ponto['mostrar'] = indice % passo == 0 or indice == quantidade - 1
        ponto['altura'] = int(altura) if altura else 0
        coords.append(f"{ponto['cx']},{ponto['y']}")
    return {
        'pontos': pontos,
        'linha': ' '.join(coords),
        'largura': round(largura, 1),
        'tem_dados': maior > 0,
    }


def serie_entre(inicio, fim):
    mapa = _mapa_por_dia(
        Pedido.objects.filter(status=Pedido.STATUS_APROVADO),
        inicio,
        fim,
        'criado_em',
        Sum('valor_total'),
    )
    grafico = _grafico(_pontos_periodo(mapa, inicio, fim))
    return grafico['pontos'], grafico['tem_dados']


def series_painel(inicio, fim):
    faturamento = _grafico(_pontos_periodo(
        _mapa_por_dia(
            Pedido.objects.filter(status=Pedido.STATUS_APROVADO),
            inicio, fim, 'criado_em', Sum('valor_total'),
        ),
        inicio, fim,
    ))
    clientes = _grafico(_pontos_periodo(
        _mapa_por_dia(
            User.objects.filter(is_staff=False),
            inicio, fim, 'date_joined', Count('id'),
        ),
        inicio, fim,
    ))
    pedidos = _grafico(_pontos_periodo(
        _mapa_por_dia(Pedido.objects.all(), inicio, fim, 'criado_em', Count('id')),
        inicio, fim,
    ))
    vendas_pts = _pontos_periodo(
        _mapa_por_dia(
            ItemPedido.objects.filter(
                pedido__status=Pedido.STATUS_APROVADO,
                modalidade=ModalidadeComercial.VENDA,
            ),
            inicio, fim, 'pedido__criado_em', Sum('quantidade'),
        ),
        inicio, fim,
    )
    alugueis_pts = _pontos_periodo(
        _mapa_por_dia(
            ItemPedido.objects.filter(
                pedido__status=Pedido.STATUS_APROVADO,
                modalidade=ModalidadeComercial.ALUGUEL,
            ),
            inicio, fim, 'pedido__criado_em', Sum('quantidade'),
        ),
        inicio, fim,
    )
    maior = max(
        [Decimal(str(ponto['total'] or 0)) for ponto in vendas_pts + alugueis_pts],
        default=Decimal('0'),
    )
    escala = maior if maior > 0 else Decimal('1')
    vendas = _grafico(vendas_pts, escala)
    alugueis = _grafico(alugueis_pts, escala)
    for venda, aluguel in zip(vendas['pontos'], alugueis['pontos']):
        venda['h2'] = aluguel['h']
        venda['y2'] = aluguel['y']
        venda['total2'] = aluguel['total']
    vendas['meia'] = max(2, round(vendas['largura'] / 2, 1))
    return {
        'faturamento': faturamento,
        'clientes': clientes,
        'pedidos': pedidos,
        'movimento': vendas,
        'tem_movimento': vendas['tem_dados'] or alugueis['tem_dados'],
    }


def _agrupar(bruto, rotulo, tamanho):
    pontos = []
    bloco = bruto[:tamanho]
    resto = bruto
    while resto:
        bloco = resto[:tamanho]
        resto = resto[tamanho:]
        inicio = bloco[0][0]
        fim = bloco[-1][0]
        total = sum((item[1] for item in bloco), Decimal('0.00'))
        pontos.append({
            'label': f'{inicio.strftime("%d/%m")}–{fim.strftime("%d/%m")}',
            'tick': rotulo(inicio),
            'total': _dinheiro(total),
        })
    return pontos


def _valor_item():
    return ExpressionWrapper(
        F('preco_unitario') * F('quantidade'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )


def ranking(modalidade, limite=5, inicio=None, fim=None):
    qs = ItemPedido.objects.filter(
        pedido__status=Pedido.STATUS_APROVADO,
        modalidade=modalidade,
    )
    if inicio:
        qs = qs.filter(pedido__criado_em__date__gte=inicio)
    if fim:
        qs = qs.filter(pedido__criado_em__date__lte=fim)
    return list(
        qs
        .values('produto_id', 'produto__titulo')
        .annotate(qtd=Sum('quantidade'), valor=Sum(_valor_item()))
        .order_by('-qtd', 'produto__titulo')[:limite]
    )


def categoria_de(produto_id, musica_ids, livro_ids, midia_ids):
    if produto_id in musica_ids:
        return 'Disco', 'gestao_disco_editar', 'gestao_disco_excluir'
    if produto_id in livro_ids:
        return 'Livro', 'gestao_livro_editar', 'gestao_livro_excluir'
    if produto_id in midia_ids:
        return 'Filme / DVD', 'gestao_midia_editar', 'gestao_midia_excluir'
    return 'Produto', None, None


def mapas_categoria():
    return (
        set(Musica.objects.values_list('pk', flat=True)),
        set(Livro.objects.values_list('pk', flat=True)),
        set(MidiaAudiovisual.objects.values_list('pk', flat=True)),
    )


def linha_produto(produto, mapas):
    categoria, editar_nome, excluir_nome = categoria_de(produto.pk, *mapas)
    venda = produto.estoque if produto.disponivel_venda else None
    aluguel = produto.estoque_aluguel if produto.disponivel_aluguel else None
    atual = produto.estoque + produto.estoque_aluguel
    if atual <= 0:
        status = 'sem'
        status_label = 'Sem estoque'
    elif (
        (produto.disponivel_venda and 0 < produto.estoque <= ESTOQUE_BAIXO_LIMITE)
        or (produto.disponivel_aluguel and 0 < produto.estoque_aluguel <= ESTOQUE_BAIXO_LIMITE)
    ):
        status = 'baixo'
        status_label = 'Estoque baixo'
    else:
        status = 'ok'
        status_label = 'Em estoque'
    return {
        'produto': produto,
        'categoria': categoria,
        'editar_url': reverse(editar_nome, args=[produto.pk]) if editar_nome else '',
        'excluir_url': reverse(excluir_nome, args=[produto.pk]) if excluir_nome else '',
        'estoque_venda': venda,
        'estoque_aluguel': aluguel,
        'estoque_atual': atual,
        'status': status,
        'status_label': status_label,
        'ativo': produto.ativo,
    }


def filtrar_estoque(produtos, situacao):
    mapas = mapas_categoria()
    linhas = [linha_produto(p, mapas) for p in produtos]
    if situacao == 'baixo':
        return [linha for linha in linhas if linha['status'] == 'baixo']
    if situacao == 'sem':
        return [linha for linha in linhas if linha['status'] == 'sem']
    if situacao == 'disponivel':
        return [linha for linha in linhas if linha['status'] == 'ok']
    return linhas


def status_aluguel(item, hoje):
    if item.pedido.status != Pedido.STATUS_APROVADO:
        return 'outro', item.pedido.get_status_display()
    if not item.data_devolucao:
        return 'ativo', 'Ativo'
    if item.data_devolucao < hoje:
        return 'atrasado', 'Atrasado'
    if item.data_devolucao <= hoje + timedelta(days=3):
        return 'vencendo', 'Próximo do vencimento'
    return 'ativo', 'Ativo'


def queryset_alugueis(situacao=''):
    hoje = timezone.localdate()
    qs = ItemPedido.objects.filter(modalidade=ModalidadeComercial.ALUGUEL).select_related(
        'pedido__cliente', 'produto', 'pedido__pagamento',
    ).order_by('data_devolucao', '-pedido__criado_em')
    if situacao == 'ativos':
        qs = qs.filter(pedido__status=Pedido.STATUS_APROVADO).filter(
            Q(data_devolucao__isnull=True) | Q(data_devolucao__gte=hoje)
        )
    elif situacao == 'vencendo':
        qs = qs.filter(
            pedido__status=Pedido.STATUS_APROVADO,
            data_devolucao__gte=hoje,
            data_devolucao__lte=hoje + timedelta(days=3),
        )
    elif situacao == 'atrasados':
        qs = qs.filter(pedido__status=Pedido.STATUS_APROVADO, data_devolucao__lt=hoje)
    elif situacao == 'hoje':
        qs = qs.filter(pedido__status=Pedido.STATUS_APROVADO, data_devolucao=hoje)
    return qs


def clientes_queryset(q='', novos=''):
    qs = User.objects.filter(is_staff=False)
    if novos == 'hoje':
        qs = qs.filter(date_joined__date=timezone.localdate())
    elif novos != 'todos':
        qs = qs.filter(pedidos__isnull=False)
    qs = qs.annotate(
        qtd_pedidos=Count('pedidos', distinct=True),
        total_gasto=Sum('pedidos__valor_total', filter=Q(pedidos__status=Pedido.STATUS_APROVADO)),
        ultima_compra=Max('pedidos__criado_em'),
        qtd_alugueis=Count(
            'pedidos__itens',
            filter=Q(
                pedidos__status=Pedido.STATUS_APROVADO,
                pedidos__itens__modalidade=ModalidadeComercial.ALUGUEL,
            ),
            distinct=True,
        ),
    ).distinct().order_by('-date_joined' if novos in ('hoje', 'todos') else '-ultima_compra')
    q = (q or '').strip()
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    return qs


def buscar(q):
    q = (q or '').strip()
    vazio = {'produtos': [], 'pedidos': [], 'clientes': [], 'alugueis': []}
    if len(q) < 2:
        return vazio
    mapas = mapas_categoria()
    produtos = []
    for produto in Produto.objects.filter(titulo__icontains=q).order_by('titulo')[:8]:
        linha = linha_produto(produto, mapas)
        produtos.append({'titulo': produto.titulo, 'url': linha['editar_url'] or reverse('gestao_produtos')})
    pedidos_qs = Pedido.objects.select_related('cliente').filter(
        Q(cliente__username__icontains=q) | Q(cliente__email__icontains=q)
    )
    if q.isdigit():
        pedidos_qs = Pedido.objects.select_related('cliente').filter(
            Q(pk=int(q)) | Q(cliente__username__icontains=q) | Q(cliente__email__icontains=q)
        )
    pedidos = [
        {
            'rotulo': f'#{pedido.id} · {pedido.cliente.username}',
            'url': reverse('gestao_pedido_detalhe', args=[pedido.pk]),
        }
        for pedido in pedidos_qs.order_by('-criado_em')[:8]
    ]
    clientes = [
        {
            'nome': user.get_full_name() or user.username,
            'url': reverse('gestao_cliente_detalhe', args=[user.pk]),
        }
        for user in User.objects.filter(is_staff=False).filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        ).order_by('username')[:8]
    ]
    alugueis = [
        {
            'rotulo': f'{item.produto.titulo} · {item.pedido.cliente.username}',
            'url': reverse('gestao_alugueis') + f'?q={item.produto.titulo}',
        }
        for item in ItemPedido.objects.filter(
            modalidade=ModalidadeComercial.ALUGUEL,
            produto__titulo__icontains=q,
        ).select_related('produto', 'pedido__cliente').order_by('-pedido__criado_em')[:8]
    ]
    return {'produtos': produtos, 'pedidos': pedidos, 'clientes': clientes, 'alugueis': alugueis}


PERIODOS_PAINEL = (
    ('hoje', 'Hoje'),
    ('ontem', 'Ontem'),
    ('7', 'Últimos 7 dias'),
    ('30', 'Últimos 30 dias'),
    ('mes', 'Este mês'),
    ('mes_anterior', 'Mês anterior'),
    ('90', 'Últimos 90 dias'),
    ('personalizado', 'Personalizado'),
)


def _data_param(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except ValueError:
        return None


def resolver_periodo(params):
    hoje = timezone.localdate()
    chave = (params.get('periodo') or 'mes').strip()
    if chave not in dict(PERIODOS_PAINEL):
        chave = 'mes'

    if chave == 'hoje':
        inicio = fim = hoje
        ant_ini = ant_fim = hoje - timedelta(days=1)
        rotulo = 'Hoje'
    elif chave == 'ontem':
        inicio = fim = hoje - timedelta(days=1)
        ant_ini = ant_fim = inicio - timedelta(days=1)
        rotulo = 'Ontem'
    elif chave == '7':
        inicio, fim, ant_ini, ant_fim = _janela(hoje, 7)
        rotulo = 'Últimos 7 dias'
    elif chave == '30':
        inicio, fim, ant_ini, ant_fim = _janela(hoje, 30)
        rotulo = 'Últimos 30 dias'
    elif chave == '90':
        inicio, fim, ant_ini, ant_fim = _janela(hoje, 90)
        rotulo = 'Últimos 90 dias'
    elif chave == 'mes_anterior':
        inicio, fim = _mes_anterior(hoje)
        ant_fim = inicio - timedelta(days=1)
        ant_ini = _inicio_mes(ant_fim)
        rotulo = 'Mês anterior'
    elif chave == 'personalizado':
        inicio = _data_param(params.get('inicio')) or _inicio_mes(hoje)
        fim = _data_param(params.get('fim')) or hoje
        if fim < inicio:
            inicio, fim = fim, inicio
        dias = (fim - inicio).days
        ant_fim = inicio - timedelta(days=1)
        ant_ini = ant_fim - timedelta(days=dias)
        rotulo = 'Personalizado'
    else:
        inicio = _inicio_mes(hoje)
        fim = hoje
        ant_ini, ant_fim = _mes_anterior(hoje)
        rotulo = 'Este mês'
        chave = 'mes'

    return {
        'chave': chave,
        'rotulo': rotulo,
        'inicio': inicio,
        'fim': fim,
        'anterior_inicio': ant_ini,
        'anterior_fim': ant_fim,
    }


def _janela(hoje, dias):
    inicio = hoje - timedelta(days=dias - 1)
    fim = hoje
    ant_fim = inicio - timedelta(days=1)
    ant_ini = ant_fim - timedelta(days=dias - 1)
    return inicio, fim, ant_ini, ant_fim


def cards_do_periodo(inicio, fim, ant_ini, ant_fim):
    atual = faturamento_entre(inicio, fim)
    anterior = faturamento_entre(ant_ini, ant_fim)
    vendas = unidades(ModalidadeComercial.VENDA, inicio, fim)
    vendas_ant = unidades(ModalidadeComercial.VENDA, ant_ini, ant_fim)
    alugueis = unidades(ModalidadeComercial.ALUGUEL, inicio, fim)
    alugueis_ant = unidades(ModalidadeComercial.ALUGUEL, ant_ini, ant_fim)
    pedidos = Pedido.objects.filter(criado_em__date__gte=inicio, criado_em__date__lte=fim).count()
    pedidos_ant = Pedido.objects.filter(criado_em__date__gte=ant_ini, criado_em__date__lte=ant_fim).count()
    hoje = timezone.localdate()
    return {
        'faturamento': _dinheiro(atual['total']),
        'faturamento_var': _variacao(atual['total'], anterior['total']),
        'ticket_medio': _dinheiro(atual['ticket']),
        'pedidos': pedidos,
        'pedidos_var': _variacao(pedidos, pedidos_ant),
        'vendas': vendas,
        'vendas_var': _variacao(vendas, vendas_ant),
        'alugueis': alugueis,
        'alugueis_var': _variacao(alugueis, alugueis_ant),
        'alugueis_ativos': ItemPedido.objects.filter(
            modalidade=ModalidadeComercial.ALUGUEL,
            pedido__status=Pedido.STATUS_APROVADO,
        ).filter(Q(data_devolucao__isnull=True) | Q(data_devolucao__gte=hoje)).count(),
        'produtos_estoque': Produto.objects.filter(ativo=True).filter(
            Q(estoque__gt=0) | Q(estoque_aluguel__gt=0)
        ).count(),
        'clientes_periodo': User.objects.filter(
            is_staff=False,
            pedidos__criado_em__date__gte=inicio,
            pedidos__criado_em__date__lte=fim,
        ).distinct().count(),
    }


def cards_dashboard():
    hoje = timezone.localdate()
    inicio = _inicio_mes(hoje)
    ant_ini, ant_fim = _mes_anterior(hoje)
    dados = cards_do_periodo(inicio, hoje, ant_ini, ant_fim)
    alertas = alertas_contagem()
    dados.update({
        'faturamento_var': dados['faturamento_var'],
        'pedidos_mes': dados['pedidos'],
        'vendas_mes': dados['vendas'],
        'estoque_baixo': alertas['estoque_baixo'],
        'sem_estoque': alertas['sem_estoque'],
        'alugueis_atrasados': alertas['alugueis_atrasados'],
        'pedidos_pendentes': alertas['pedidos_pendentes'],
        'clientes': User.objects.filter(is_staff=False, pedidos__isnull=False).distinct().count(),
    })
    return dados


def itens_atencao():
    hoje = timezone.localdate()
    alertas = alertas_contagem()
    itens = []

    def add(nivel, titulo, detalhe, url, acao, url_extra='', acao_extra=''):
        itens.append({
            'nivel': nivel,
            'titulo': titulo,
            'detalhe': detalhe,
            'url': url,
            'acao': acao,
            'url_extra': url_extra,
            'acao_extra': acao_extra,
        })

    if alertas['alugueis_atrasados']:
        n = alertas['alugueis_atrasados']
        add(
            'critico',
            '1 aluguel atrasado' if n == 1 else f'{n} aluguéis atrasados',
            'A data prevista de devolução já passou.',
            reverse('gestao_alugueis') + '?situacao=atrasados',
            'Ver agora',
            reverse('gestao_alugueis') + '?situacao=atrasados',
            'Acompanhar aluguel',
        )
    if alertas['pedidos_aguardando']:
        n = alertas['pedidos_aguardando']
        add(
            'critico',
            f'{n} pedido{"s" if n != 1 else ""} aguardando pagamento',
            'Ainda não houve confirmação do pagamento.',
            reverse('gestao_pedidos_lista') + '?status=aguardando_pagamento',
            'Ver agora',
            reverse('gestao_pedidos_lista') + '?status=aguardando_pagamento',
            'Abrir pedidos',
        )
    if alertas['sem_estoque']:
        nomes = list(
            Produto.objects.filter(ativo=True, estoque=0, estoque_aluguel=0).order_by('titulo').values_list('titulo', flat=True)[:3]
        )
        extra = f' Inclui: {", ".join(nomes)}.' if nomes else ''
        n = alertas['sem_estoque']
        add(
            'critico',
            '1 produto sem estoque' if n == 1 else f'{n} produtos sem estoque',
            f'Sem unidade para venda ou aluguel.{extra}',
            reverse('gestao_estoque') + '?situacao=sem',
            'Ver agora',
            reverse('gestao_estoque') + '?situacao=sem',
            'Atualizar estoque',
        )
    if alertas['estoque_baixo']:
        n = alertas['estoque_baixo']
        add(
            'atencao',
            '1 produto abaixo do estoque mínimo' if n == 1 else f'{n} produtos abaixo do estoque mínimo',
            f'Mínimo configurado: {ESTOQUE_BAIXO_LIMITE} unidades.',
            reverse('gestao_estoque') + '?situacao=baixo',
            'Ver agora',
            reverse('gestao_estoque') + '?situacao=baixo',
            'Atualizar estoque',
        )
    if alertas['alugueis_vencendo']:
        n = alertas['alugueis_vencendo']
        add(
            'atencao',
            '1 aluguel próximo do vencimento' if n == 1 else f'{n} aluguéis próximos do vencimento',
            'Devolução prevista nos próximos 3 dias.',
            reverse('gestao_alugueis') + '?situacao=vencendo',
            'Ver agora',
        )
    if alertas['pedidos_analise']:
        n = alertas['pedidos_analise']
        add(
            'atencao',
            '1 pagamento em análise' if n == 1 else f'{n} pagamentos em análise',
            'O pedido está marcado como em análise.',
            reverse('gestao_pedidos_lista') + '?status=em_analise',
            'Ver agora',
        )
    return itens


def resumo_hoje():
    hoje = timezone.localdate()
    return {
        'vendas': unidades(ModalidadeComercial.VENDA, hoje, hoje),
        'faturamento': _dinheiro(faturamento_entre(hoje, hoje)['total']),
        'pedidos': Pedido.objects.filter(criado_em__date=hoje).count(),
        'alugueis': unidades(ModalidadeComercial.ALUGUEL, hoje, hoje),
        'devolucoes_hoje': ItemPedido.objects.filter(
            modalidade=ModalidadeComercial.ALUGUEL,
            pedido__status=Pedido.STATUS_APROVADO,
            data_devolucao=hoje,
        ).count(),
        'devolucoes_atrasadas': ItemPedido.objects.filter(
            modalidade=ModalidadeComercial.ALUGUEL,
            pedido__status=Pedido.STATUS_APROVADO,
            data_devolucao__lt=hoje,
        ).count(),
        'novos_clientes': User.objects.filter(is_staff=False, date_joined__date=hoje).count(),
        'data': hoje,
    }


def categorias_periodo(inicio, fim):
    mapas = mapas_categoria()
    linhas = ItemPedido.objects.filter(
        pedido__status=Pedido.STATUS_APROVADO,
        modalidade=ModalidadeComercial.VENDA,
        pedido__criado_em__date__gte=inicio,
        pedido__criado_em__date__lte=fim,
    ).values('produto_id').annotate(valor=Sum(_valor_item()))
    totais = {'Música': Decimal('0.00'), 'Livros': Decimal('0.00'), 'Filmes': Decimal('0.00'), 'Outros': Decimal('0.00')}
    for linha in linhas:
        categoria, _, _ = categoria_de(linha['produto_id'], *mapas)
        chave = {'Disco': 'Música', 'Livro': 'Livros', 'Filme / DVD': 'Filmes'}.get(categoria, 'Outros')
        totais[chave] += _dinheiro(linha['valor'])
    soma = sum(totais.values(), Decimal('0.00'))
    if soma <= 0:
        return [], ''
    cores = {'Música': '#D4AF68', 'Livros': '#8ef0c2', 'Filmes': '#7eb6ff', 'Outros': '#A7ACB5'}
    partes = []
    giro = 0
    fatias = []
    for nome, valor in totais.items():
        if valor <= 0:
            continue
        pct = round(float(valor / soma * 100), 1)
        fim_giro = giro + pct
        partes.append(f'{cores[nome]} {giro}% {fim_giro}%')
        giro = fim_giro
        fatias.append({'nome': nome, 'valor': valor, 'pct': pct, 'cor': cores[nome]})
    return fatias, ', '.join(partes)


def clientes_top(inicio, fim, limite=5):
    return list(
        User.objects.filter(
            is_staff=False,
            pedidos__status=Pedido.STATUS_APROVADO,
            pedidos__criado_em__date__gte=inicio,
            pedidos__criado_em__date__lte=fim,
        ).annotate(
            total=Sum(
                'pedidos__valor_total',
                filter=Q(
                    pedidos__status=Pedido.STATUS_APROVADO,
                    pedidos__criado_em__date__gte=inicio,
                    pedidos__criado_em__date__lte=fim,
                ),
            ),
            qtd=Count(
                'pedidos',
                filter=Q(
                    pedidos__status=Pedido.STATUS_APROVADO,
                    pedidos__criado_em__date__gte=inicio,
                    pedidos__criado_em__date__lte=fim,
                ),
                distinct=True,
            ),
        ).filter(total__gt=0).order_by('-total')[:limite]
    )


def produtos_parados(inicio, fim, limite=6):
    movidos = ItemPedido.objects.filter(
        pedido__status=Pedido.STATUS_APROVADO,
        pedido__criado_em__date__gte=inicio,
        pedido__criado_em__date__lte=fim,
    ).values_list('produto_id', flat=True)
    return list(Produto.objects.filter(ativo=True).exclude(pk__in=movidos).order_by('titulo')[:limite])


def insight_venda(inicio, fim, ant_ini, ant_fim):
    atual = ranking(ModalidadeComercial.VENDA, limite=1, inicio=inicio, fim=fim)
    if not atual:
        return ''
    titulo = atual[0]['produto__titulo']
    qtd = atual[0]['qtd'] or 0
    anterior = ItemPedido.objects.filter(
        pedido__status=Pedido.STATUS_APROVADO,
        modalidade=ModalidadeComercial.VENDA,
        produto_id=atual[0]['produto_id'],
        pedido__criado_em__date__gte=ant_ini,
        pedido__criado_em__date__lte=ant_fim,
    ).aggregate(qtd=Sum('quantidade'))['qtd'] or 0
    if anterior > 0 and qtd > anterior:
        return f'{titulo} vendeu mais neste período ({qtd} un. contra {anterior} no período anterior).'
    return ''


def ultimas_atividades(limite=12):
    eventos = []
    for pedido in Pedido.objects.select_related('cliente').order_by('-criado_em')[:limite]:
        eventos.append({
            'quando': pedido.criado_em,
            'texto': f'Novo pedido #{pedido.id} · {pedido.cliente.username}',
            'url': reverse('gestao_pedido_detalhe', args=[pedido.pk]),
        })
    for pagamento in Pagamento.objects.select_related('pedido').order_by('-atualizado_em')[:limite]:
        eventos.append({
            'quando': pagamento.atualizado_em,
            'texto': f'Pagamento {pagamento.status} no pedido #{pagamento.pedido_id}',
            'url': reverse('gestao_pedido_detalhe', args=[pagamento.pedido_id]),
        })
    for produto in Produto.objects.order_by('-criado_em')[:limite]:
        eventos.append({
            'quando': produto.criado_em,
            'texto': f'Produto cadastrado · {produto.titulo}',
            'url': reverse('gestao_produtos') + '?q=' + quote(produto.titulo),
        })
    for item in ItemPedido.objects.filter(
        modalidade=ModalidadeComercial.ALUGUEL,
    ).select_related('produto', 'pedido__cliente', 'pedido').order_by('-pedido__criado_em')[:limite]:
        eventos.append({
            'quando': item.pedido.criado_em,
            'texto': f'Aluguel iniciado · {item.produto.titulo}',
            'url': reverse('gestao_alugueis') + '?q=' + quote(item.produto.titulo),
        })
    eventos.sort(key=lambda evento: evento['quando'], reverse=True)
    return eventos[:limite]
