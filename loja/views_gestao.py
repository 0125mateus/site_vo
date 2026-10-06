import logging
from functools import wraps

import csv
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .assistant_intent import INTENT_LABELS_CLIENTE, INTENT_LABELS_GESTOR, classify_intent
from .forms_gestao import (
    AcessoClienteForm,
    FraseTreinoForm,
    ImportarCatalogoForm,
    LivroForm,
    MidiaForm,
    MusicaForm,
    PlanoClubeForm,
    TestarIntencaoForm,
)
from .gestao_services import ESTOQUE_BAIXO_LIMITE, gerar_descricao_produto, importar_catalogo_csv
from .models import (
    FraseTreinoAssistente,
    ItemPedido,
    Livro,
    MidiaAudiovisual,
    ModalidadeComercial,
    Musica,
    Pedido,
    PlanoClube,
    Produto,
)
from .painel_gestao import (
    alertas_contagem,
    buscar,
    cards_do_periodo,
    categorias_periodo,
    clientes_queryset,
    clientes_top,
    filtrar_estoque,
    insight_venda,
    itens_atencao,
    linha_produto,
    mapas_categoria,
    produtos_parados,
    queryset_alugueis,
    ranking,
    resolver_periodo,
    resumo_hoje,
    serie_entre,
    series_painel,
    status_aluguel,
    ultimas_atividades,
)

logger = logging.getLogger(__name__)


def _salvar_form_produto(request, form, sucesso_msg, redirect_name):
    if not form.is_valid():
        return False
    try:
        form.save()
    except Exception as erro:
        logger.exception('Falha ao salvar arquivo de mídia no gestor')
        texto = str(erro).lower()
        if 'arquivo-grande' in texto or '413' in texto or 'payload too large' in texto or 'maximum allowed size' in texto:
            messages.error(
                request,
                'O arquivo passou de 48 MB. A nuvem gratuita não guarda um filme inteiro. '
                'Envie só a capa e coloque o trailer no link do YouTube.',
            )
        else:
            messages.error(
                request,
                'Não foi possível enviar o arquivo. A capa aceita JPG, PNG ou WebP. '
                'O filme completo aceita MP4, MKV, AVI ou ISO de até 48 MB.',
            )
        return False
    messages.success(request, sucesso_msg)
    return redirect(redirect_name)


def _excluir_item_catalogo(request, objeto, lista_url, rotulo):
    titulo = objeto.titulo
    tem_pedidos = ItemPedido.objects.filter(produto_id=objeto.pk).exists()
    if request.method == 'POST':
        if request.POST.get('acao') == 'desativar':
            objeto.ativo = False
            objeto.save(update_fields=['ativo'])
            messages.success(request, f'{rotulo} "{titulo}" desativado e oculto da loja.')
            return redirect(lista_url)
        if tem_pedidos:
            messages.error(
                request,
                f'Não dá para excluir "{titulo}" porque já existe em um pedido. '
                'Desative o item para tirá-lo da loja sem apagar o histórico de vendas.',
            )
            return redirect(request.path)
        try:
            objeto.delete()
        except ProtectedError:
            messages.error(
                request,
                f'Não dá para excluir "{titulo}" porque já existe em um pedido. '
                'Desative o item para tirá-lo da loja.',
            )
            return redirect(request.path)
        except Exception:
            logger.exception('Falha ao excluir %s pk=%s', rotulo, objeto.pk)
            messages.error(
                request,
                f'Não foi possível excluir "{titulo}". Tente desativar o item.',
            )
            return redirect(request.path)
        messages.success(request, f'{rotulo} "{titulo}" removido.')
        return redirect(lista_url)
    return render(request, 'gestao/confirmar_exclusao.html', {
        'objeto': objeto,
        'tipo': rotulo.lower(),
        'voltar_url': lista_url,
        'tem_pedidos': tem_pedidos,
        'pode_desativar': True,
    })


def gestor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


def gestao_entrar(request):
    return redirect('gestao_dashboard')


@gestor_required
def dashboard(request):
    periodo = resolver_periodo(request.GET)
    hora = timezone.localtime().hour
    if hora < 12:
        saudacao = 'Bom dia'
    elif hora < 18:
        saudacao = 'Boa tarde'
    else:
        saudacao = 'Boa noite'
    inicio, fim = periodo['inicio'], periodo['fim']
    serie, tem_serie = serie_entre(inicio, fim)
    graficos = series_painel(inicio, fim)
    fatias, gradiente = categorias_periodo(inicio, fim)
    return render(request, 'gestao/dashboard.html', {
        'saudacao': saudacao,
        'periodo': periodo,
        'periodos': (
            ('hoje', 'Hoje'),
            ('ontem', 'Ontem'),
            ('7', 'Últimos 7 dias'),
            ('30', 'Últimos 30 dias'),
            ('mes', 'Este mês'),
            ('mes_anterior', 'Mês anterior'),
            ('90', 'Últimos 90 dias'),
            ('personalizado', 'Personalizado'),
        ),
        'cards': cards_do_periodo(inicio, fim, periodo['anterior_inicio'], periodo['anterior_fim']),
        'serie': serie,
        'tem_serie': tem_serie,
        'graficos': graficos,
        'fatias': fatias,
        'gradiente': gradiente,
        'mais_vendidos': ranking(ModalidadeComercial.VENDA, inicio=inicio, fim=fim),
        'mais_alugados': ranking(ModalidadeComercial.ALUGUEL, inicio=inicio, fim=fim),
        'atencao': itens_atencao(),
        'hoje': resumo_hoje(),
        'parados': produtos_parados(inicio, fim),
        'tem_catalogo': Produto.objects.filter(ativo=True).exists(),
        'clientes_top': clientes_top(inicio, fim),
        'insight': insight_venda(inicio, fim, periodo['anterior_inicio'], periodo['anterior_fim']),
        'atividades': ultimas_atividades(),
        'ultimos_pedidos': Pedido.objects.select_related('cliente').prefetch_related('itens__produto').order_by('-criado_em')[:5],
        'alugueis_andamento': queryset_alugueis('ativos')[:5],
    })


@gestor_required
def discos_lista(request):
    discos = Musica.objects.order_by('-criado_em')
    return render(request, 'gestao/discos_lista.html', {'discos': discos})


@gestor_required
def disco_criar(request):
    form = MusicaForm(request.POST or None, request.FILES or None)
    salvo = _salvar_form_produto(
        request, form, f'Disco "{form.instance.titulo}" cadastrado.', 'gestao_discos_lista',
    )
    if salvo:
        return salvo
    return render(request, 'gestao/form.html', {
        'form': form,
        'titulo_pagina': 'Novo disco',
        'tipo': 'disco',
        'voltar_url': 'gestao_discos_lista',
    })


@gestor_required
def disco_editar(request, pk):
    disco = get_object_or_404(Musica, pk=pk)
    form = MusicaForm(request.POST or None, request.FILES or None, instance=disco)
    salvo = _salvar_form_produto(
        request, form, f'Disco "{disco.titulo}" atualizado.', 'gestao_discos_lista',
    )
    if salvo:
        return salvo
    return render(request, 'gestao/form.html', {
        'form': form,
        'titulo_pagina': f'Editar: {disco.titulo}',
        'tipo': 'disco',
        'objeto': disco,
        'voltar_url': 'gestao_discos_lista',
    })


@gestor_required
def disco_excluir(request, pk):
    disco = get_object_or_404(Musica, pk=pk)
    return _excluir_item_catalogo(request, disco, 'gestao_discos_lista', 'Disco')


@gestor_required
def livros_lista(request):
    livros = Livro.objects.order_by('-criado_em')
    return render(request, 'gestao/livros_lista.html', {'livros': livros})


@gestor_required
def livro_criar(request):
    form = LivroForm(request.POST or None, request.FILES or None)
    salvo = _salvar_form_produto(
        request, form, f'Livro "{form.instance.titulo}" cadastrado.', 'gestao_livros_lista',
    )
    if salvo:
        return salvo
    return render(request, 'gestao/form.html', {
        'form': form,
        'titulo_pagina': 'Novo livro',
        'tipo': 'livro',
        'voltar_url': 'gestao_livros_lista',
    })


@gestor_required
def livro_editar(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    form = LivroForm(request.POST or None, request.FILES or None, instance=livro)
    salvo = _salvar_form_produto(
        request, form, f'Livro "{livro.titulo}" atualizado.', 'gestao_livros_lista',
    )
    if salvo:
        return salvo
    return render(request, 'gestao/form.html', {
        'form': form,
        'titulo_pagina': f'Editar: {livro.titulo}',
        'tipo': 'livro',
        'objeto': livro,
        'voltar_url': 'gestao_livros_lista',
    })


@gestor_required
def livro_excluir(request, pk):
    livro = get_object_or_404(Livro, pk=pk)
    return _excluir_item_catalogo(request, livro, 'gestao_livros_lista', 'Livro')


@gestor_required
def midias_lista(request):
    midias = MidiaAudiovisual.objects.order_by('-criado_em')
    return render(request, 'gestao/midias_lista.html', {'midias': midias})


@gestor_required
def midia_criar(request):
    form = MidiaForm(request.POST or None, request.FILES or None)
    salvo = _salvar_form_produto(
        request, form, f'Mídia "{form.instance.titulo}" cadastrada.', 'gestao_midias_lista',
    )
    if salvo:
        return salvo
    return render(request, 'gestao/form.html', {
        'form': form,
        'titulo_pagina': 'Nova mídia (filme / DVD / vídeo)',
        'tipo': 'midia',
        'voltar_url': 'gestao_midias_lista',
    })


@gestor_required
def midia_editar(request, pk):
    midia = get_object_or_404(MidiaAudiovisual, pk=pk)
    form = MidiaForm(request.POST or None, request.FILES or None, instance=midia)
    salvo = _salvar_form_produto(
        request, form, f'Mídia "{midia.titulo}" atualizada.', 'gestao_midias_lista',
    )
    if salvo:
        return salvo
    return render(request, 'gestao/form.html', {
        'form': form,
        'titulo_pagina': f'Editar: {midia.titulo}',
        'tipo': 'midia',
        'objeto': midia,
        'voltar_url': 'gestao_midias_lista',
    })


@gestor_required
def midia_excluir(request, pk):
    midia = get_object_or_404(MidiaAudiovisual, pk=pk)
    return _excluir_item_catalogo(request, midia, 'gestao_midias_lista', 'Mídia')


@gestor_required
def assistente_frases(request):
    audiencia = request.GET.get('audiencia', FraseTreinoAssistente.AUDIENCIA_CLIENTE)
    if audiencia not in (FraseTreinoAssistente.AUDIENCIA_CLIENTE, FraseTreinoAssistente.AUDIENCIA_GESTOR):
        audiencia = FraseTreinoAssistente.AUDIENCIA_CLIENTE

    frases = FraseTreinoAssistente.objects.filter(audiencia=audiencia)
    form = FraseTreinoForm(request.POST or None, audiencia=audiencia)
    teste_form = TestarIntencaoForm(request.POST or None, prefix='teste')
    resultado_teste = None

    if request.method == 'POST' and 'testar' in request.POST:
        if teste_form.is_valid():
            aud = teste_form.cleaned_data['audiencia']
            msg = teste_form.cleaned_data['mensagem']
            resultado_teste = classify_intent(msg, aud)
    elif request.method == 'POST' and 'adicionar' in request.POST:
        if form.is_valid():
            form.save()
            messages.success(request, 'Frase de treino adicionada. O classificador já foi atualizado.')
            return redirect(f'{reverse("gestao_assistente_frases")}?audiencia={form.instance.audiencia}')

    labels = INTENT_LABELS_GESTOR if audiencia == 'gestor' else INTENT_LABELS_CLIENTE
    return render(request, 'gestao/assistente_frases.html', {
        'frases': frases,
        'form': form,
        'teste_form': teste_form,
        'audiencia': audiencia,
        'intent_labels': labels,
        'resultado_teste': resultado_teste,
        'total_frases': frases.count(),
    })


@gestor_required
def assistente_frase_excluir(request, pk):
    frase = get_object_or_404(FraseTreinoAssistente, pk=pk)
    audiencia = frase.audiencia
    if request.method == 'POST':
        frase.delete()
        messages.success(request, 'Frase removida.')
        return redirect(f'{reverse("gestao_assistente_frases")}?audiencia={audiencia}')
    return render(request, 'gestao/confirmar_exclusao.html', {
        'objeto': frase,
        'tipo': 'frase',
        'voltar_url': 'gestao_assistente_frases',
    })


@gestor_required
def pedidos_lista(request):
    status = request.GET.get('status', '')
    q = (request.GET.get('q') or '').strip()
    pedidos = Pedido.objects.select_related('cliente', 'pagamento').prefetch_related('itens__produto').order_by('-criado_em')
    if status:
        pedidos = pedidos.filter(status=status)
    if q:
        filtro = Q(cliente__username__icontains=q) | Q(cliente__email__icontains=q) | Q(itens__produto__titulo__icontains=q)
        if q.isdigit():
            filtro |= Q(pk=int(q))
        pedidos = pedidos.filter(filtro).distinct()
    return render(request, 'gestao/pedidos_lista.html', {
        'pedidos': pedidos,
        'filtro_status': status,
        'q': q,
        'status_choices': Pedido.STATUS_CHOICES,
    })


@gestor_required
def pedido_detalhe(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('cliente', 'plano_clube').prefetch_related('itens__produto'),
        pk=pk,
    )
    return render(request, 'gestao/pedido_detalhe.html', {'pedido': pedido})


@gestor_required
@require_POST
def gerar_descricao_ia(request):
    titulo = (request.POST.get('titulo') or '').strip()
    tipo = (request.POST.get('tipo') or 'livro').strip()
    extra = (request.POST.get('extra') or '').strip()
    if not titulo:
        return JsonResponse({'ok': False, 'detail': 'Informe o título.'}, status=400)
    try:
        descricao = gerar_descricao_produto(titulo, tipo, extra)
    except ValueError as exc:
        return JsonResponse({'ok': False, 'detail': str(exc)}, status=400)
    except Exception:
        logger.exception('Falha ao gerar descrição IA')
        return JsonResponse({'ok': False, 'detail': 'Erro ao gerar descrição.'}, status=502)
    return JsonResponse({'ok': True, 'descricao': descricao})


@gestor_required
def planos_clube_lista(request):
    planos = PlanoClube.objects.order_by('ordem', 'titulo')
    return render(request, 'gestao/planos_clube_lista.html', {'planos': planos})


@gestor_required
def plano_clube_criar(request):
    form = PlanoClubeForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, f'Plano "{form.instance.titulo}" criado.')
        return redirect('gestao_planos_clube_lista')
    return render(request, 'gestao/form_plano_clube.html', {
        'form': form,
        'titulo_pagina': 'Novo plano do clube',
    })


@gestor_required
def plano_clube_editar(request, pk):
    plano = get_object_or_404(PlanoClube, pk=pk)
    form = PlanoClubeForm(request.POST or None, instance=plano)
    if form.is_valid():
        form.save()
        messages.success(request, f'Plano "{plano.titulo}" atualizado.')
        return redirect('gestao_planos_clube_lista')
    return render(request, 'gestao/form_plano_clube.html', {
        'form': form,
        'titulo_pagina': f'Editar: {plano.titulo}',
        'plano': plano,
    })


@gestor_required
def importar_catalogo(request):
    form = ImportarCatalogoForm(request.POST or None, request.FILES or None)
    resultado = None
    if request.method == 'POST' and form.is_valid():
        resultado = importar_catalogo_csv(form.cleaned_data['arquivo'])
        if resultado['criados']:
            messages.success(request, f'{resultado["criados"]} item(ns) importado(s).')
        if resultado['erros']:
            messages.warning(request, f'{len(resultado["erros"])} linha(s) com erro.')
        if resultado['criados'] and not resultado['erros']:
            return redirect('gestao_dashboard')
    return render(request, 'gestao/importar_catalogo.html', {
        'form': form,
        'resultado': resultado,
    })


def _produtos_filtrados(q):
    qs = Produto.objects.order_by('titulo')
    if q:
        qs = qs.filter(titulo__icontains=q)
    mapas = mapas_categoria()
    return [linha_produto(produto, mapas) for produto in qs]


@gestor_required
def produtos_lista(request):
    q = (request.GET.get('q') or '').strip()
    return render(request, 'gestao/produtos.html', {
        'linhas': _produtos_filtrados(q),
        'q': q,
    })


@gestor_required
def estoque_lista(request):
    q = (request.GET.get('q') or '').strip()
    situacao = request.GET.get('situacao', '')
    if situacao not in ('', 'baixo', 'sem', 'disponivel'):
        situacao = ''
    qs = Produto.objects.order_by('titulo')
    if q:
        qs = qs.filter(titulo__icontains=q)
    return render(request, 'gestao/estoque.html', {
        'linhas': filtrar_estoque(qs, situacao),
        'q': q,
        'situacao': situacao,
        'limite': ESTOQUE_BAIXO_LIMITE,
    })


@gestor_required
def alugueis_lista(request):
    situacao = request.GET.get('situacao', '')
    q = (request.GET.get('q') or '').strip()
    if situacao not in ('', 'ativos', 'vencendo', 'atrasados', 'devolvidos', 'hoje'):
        situacao = ''
    hoje = timezone.localdate()
    itens = []
    if situacao != 'devolvidos':
        qs = queryset_alugueis(situacao)
        if q:
            qs = qs.filter(
                Q(produto__titulo__icontains=q)
                | Q(pedido__cliente__username__icontains=q)
                | Q(pedido__cliente__email__icontains=q)
            )
        for item in qs:
            codigo, rotulo = status_aluguel(item, hoje)
            dias = None
            if item.data_devolucao:
                dias = (item.data_devolucao - hoje).days
            itens.append({'item': item, 'codigo': codigo, 'rotulo': rotulo, 'dias': dias})
    return render(request, 'gestao/alugueis.html', {
        'itens': itens,
        'situacao': situacao,
        'q': q,
        'hoje': hoje,
    })


@gestor_required
def clientes_lista(request):
    q = (request.GET.get('q') or '').strip()
    novos = request.GET.get('novos', '')
    if novos not in ('', 'hoje', 'todos'):
        novos = ''
    return render(request, 'gestao/clientes.html', {
        'clientes': clientes_queryset(q, novos),
        'q': q,
        'novos': novos,
    })


@gestor_required
def clientes_excluir(request):
    if request.method != 'POST':
        return redirect('gestao_clientes')
    User = get_user_model()
    ids = request.POST.getlist('ids')
    escolhidos = User.objects.filter(pk__in=ids, is_staff=False).exclude(pk=request.user.pk)
    voltar = redirect(f"{reverse('gestao_clientes')}?novos={request.POST.get('novos', '')}&q={request.POST.get('q', '')}")
    if request.POST.get('acao') == 'excluir':
        apagados = []
        bloqueados = []
        for usuario in escolhidos:
            if usuario.pedidos.exists():
                bloqueados.append(usuario.username)
                continue
            nome = usuario.username
            usuario.delete()
            apagados.append(nome)
        if apagados:
            messages.success(request, 'Excluído: ' + ', '.join(apagados) + '.')
        if bloqueados:
            messages.error(
                request,
                'Não excluído, porque já tem pedido: ' + ', '.join(bloqueados) + '.',
            )
        if not apagados and not bloqueados:
            messages.error(request, 'Nenhum cliente selecionado.')
        return voltar
    if not escolhidos.exists():
        messages.error(request, 'Nenhum cliente selecionado.')
        return voltar
    return render(request, 'gestao/clientes_excluir.html', {
        'clientes': escolhidos,
        'novos': request.POST.get('novos', ''),
        'q': request.POST.get('q', ''),
    })


@gestor_required
def cliente_detalhe(request, pk):
    usuario = get_object_or_404(get_user_model(), pk=pk, is_staff=False)
    form = AcessoClienteForm(request.POST or None, usuario=usuario)
    if request.method == 'POST' and form.is_valid():
        form.salvar()
        messages.success(request, f'Senha de {usuario.username} atualizada. A senha anterior deixa de valer.')
        return redirect('gestao_cliente_detalhe', pk=usuario.pk)
    pedidos = Pedido.objects.filter(cliente=usuario).prefetch_related('itens__produto').order_by('-criado_em')
    return render(request, 'gestao/cliente_detalhe.html', {
        'cliente_loja': usuario,
        'pedidos': pedidos,
        'acesso_form': form,
    })


def _parse_data(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except ValueError:
        return None


@gestor_required
def relatorios(request):
    hoje = timezone.localdate()
    inicio = _parse_data(request.GET.get('inicio')) or hoje.replace(day=1)
    fim = _parse_data(request.GET.get('fim')) or hoje
    if fim < inicio:
        inicio, fim = fim, inicio
    tipo = request.GET.get('tipo', '')
    if tipo not in ('', 'venda', 'aluguel'):
        tipo = ''
    q = (request.GET.get('q') or '').strip()
    itens = ItemPedido.objects.filter(
        pedido__status=Pedido.STATUS_APROVADO,
        pedido__criado_em__date__gte=inicio,
        pedido__criado_em__date__lte=fim,
    ).select_related('produto', 'pedido__cliente')
    if tipo:
        itens = itens.filter(modalidade=tipo)
    if q:
        itens = itens.filter(produto__titulo__icontains=q)
    if request.GET.get('export') == 'csv':
        resposta = HttpResponse(content_type='text/csv; charset=utf-8')
        resposta['Content-Disposition'] = 'attachment; filename="relatorio-vinil-pagina.csv"'
        resposta.write('\ufeff')
        writer = csv.writer(resposta)
        writer.writerow(['Data', 'Pedido', 'Cliente', 'Produto', 'Tipo', 'Quantidade', 'Valor'])
        for item in itens.order_by('-pedido__criado_em'):
            writer.writerow([
                item.pedido.criado_em.strftime('%d/%m/%Y'),
                item.pedido_id,
                item.pedido.cliente.username,
                item.produto.titulo,
                item.get_modalidade_display(),
                item.quantidade,
                item.subtotal,
            ])
        return resposta
    from decimal import Decimal

    from django.db.models import Sum

    total = sum((item.subtotal for item in itens), Decimal('0.00'))
    vendas = itens.filter(modalidade=ModalidadeComercial.VENDA).count()
    alugueis = itens.filter(modalidade=ModalidadeComercial.ALUGUEL).count()
    pedidos_n = itens.values('pedido_id').distinct().count()
    ticket = (total / pedidos_n) if pedidos_n else Decimal('0.00')

    def _top(modalidade):
        return list(
            itens.filter(modalidade=modalidade)
            .values('produto__titulo')
            .annotate(qtd=Sum('quantidade'))
            .order_by('-qtd', 'produto__titulo')[:5]
        )

    return render(request, 'gestao/relatorios.html', {
        'inicio': inicio,
        'fim': fim,
        'tipo': tipo,
        'q': q,
        'total': total,
        'vendas': vendas,
        'alugueis': alugueis,
        'pedidos_n': pedidos_n,
        'ticket': ticket,
        'mais_vendidos': _top(ModalidadeComercial.VENDA),
        'mais_alugados': _top(ModalidadeComercial.ALUGUEL),
        'itens': itens.order_by('-pedido__criado_em')[:80],
    })


@gestor_required
def configuracoes(request):
    return render(request, 'gestao/configuracoes.html')


@gestor_required
def busca(request):
    q = (request.GET.get('q') or '').strip()
    grupos = buscar(q)
    if request.GET.get('formato') == 'json':
        return JsonResponse(grupos)
    return render(request, 'gestao/busca.html', {'q': q, 'grupos': grupos})
