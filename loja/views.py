import logging
from decimal import Decimal

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from .mercadopago_service import (
    MercadoPagoAPIError,
    aplicar_pagamento_ao_pedido,
    buscar_pagamento,
    criar_preferencia_pagamento,
    sincronizar_pedido_com_mercadopago,
    validar_assinatura_webhook,
)
from .models import ItemPedido, Livro, MidiaAudiovisual, ModalidadeComercial, Musica, Pedido, Produto

logger = logging.getLogger(__name__)

CARRINHO_SESSION_KEY = 'carrinho'


def _get_carrinho(request):
    """Carrinho: { '12:venda': {'produto_id': 12, 'modalidade': 'venda', 'quantidade': 1}, ... }"""
    raw = request.session.get(CARRINHO_SESSION_KEY, {})
    # Migração do formato antigo {produto_id: qty}
    if raw and all(isinstance(v, int) for v in raw.values()):
        migrated = {}
        for pid, qty in raw.items():
            key = f'{pid}:{ModalidadeComercial.VENDA}'
            migrated[key] = {
                'produto_id': int(pid),
                'modalidade': ModalidadeComercial.VENDA,
                'quantidade': qty,
            }
        request.session[CARRINHO_SESSION_KEY] = migrated
        request.session.modified = True
        return migrated
    return raw


def _set_carrinho(request, carrinho):
    request.session[CARRINHO_SESSION_KEY] = carrinho
    request.session.modified = True


def _carrinho_total_itens(carrinho):
    return sum(item.get('quantidade', 0) for item in carrinho.values())


def _resolver_produto(produto_id):
    """Retorna produto ativo com metadados do subtipo (disco, livro, mídia)."""
    produto = get_object_or_404(Produto, pk=produto_id, ativo=True)
    musica = Musica.objects.filter(pk=produto_id).first()
    if musica:
        return {
            'produto': musica,
            'tipo': 'musica',
            'tipo_label': 'Disco',
            'subtitulo': musica.artista,
            'meta_extra': musica.formato,
        }
    livro = Livro.objects.filter(pk=produto_id).first()
    if livro:
        return {
            'produto': livro,
            'tipo': 'livro',
            'tipo_label': 'Livro',
            'subtitulo': livro.autor,
            'meta_extra': livro.isbn or '',
        }
    midia = MidiaAudiovisual.objects.filter(pk=produto_id).first()
    if midia:
        partes = [midia.get_tipo_display()]
        if midia.diretor:
            partes.append(midia.diretor)
        if midia.ano:
            partes.append(str(midia.ano))
        return {
            'produto': midia,
            'tipo': 'midia',
            'tipo_label': midia.get_tipo_display(),
            'subtitulo': midia.diretor or midia.get_tipo_display(),
            'meta_extra': ' · '.join(partes),
            'midia': midia,
        }
    return {
        'produto': produto,
        'tipo': 'produto',
        'tipo_label': 'Item',
        'subtitulo': '',
        'meta_extra': '',
    }


def _tipo_midia_arquivo(produto) -> str:
    nome = (produto.arquivo.name if produto.arquivo else '').lower()
    if nome.endswith(('.mp3', '.flac', '.ogg', '.wav', '.m4a', '.aac')):
        return 'audio'
    if nome.endswith(('.mp4', '.webm', '.mkv', '.mov')):
        return 'video'
    if nome.endswith('.pdf'):
        return 'pdf'
    return 'file'


def busca(request):
    q = request.GET.get('q', '').strip()
    musicas = livros = midias = []
    total = 0

    if q:
        musicas = Musica.objects.filter(
            ativo=True,
        ).filter(Q(titulo__icontains=q) | Q(artista__icontains=q))
        livros = Livro.objects.filter(
            ativo=True,
        ).filter(Q(titulo__icontains=q) | Q(autor__icontains=q) | Q(isbn__icontains=q))
        midias = MidiaAudiovisual.objects.filter(
            ativo=True,
        ).filter(Q(titulo__icontains=q) | Q(diretor__icontains=q))
        total = musicas.count() + livros.count() + midias.count()

    return render(request, 'loja/busca.html', {
        'q': q,
        'musicas': musicas,
        'livros': livros,
        'midias': midias,
        'total': total,
    })


def _catalogo_response(request, secao, titulo, eyebrow, queryset, catalog_class, total_label, tipo):
    return render(request, 'loja/catalogo.html', {
        'secao': secao,
        'tipo': tipo,
        'titulo': titulo,
        'eyebrow': eyebrow,
        'itens': queryset.filter(ativo=True),
        'total': queryset.filter(ativo=True).count(),
        'catalog_class': catalog_class,
        'total_label': total_label,
    })


def catalogo_discos(request):
    return _catalogo_response(
        request, 'discos', 'Na prateleira dos discos', 'Vinil · Disqueira',
        Musica.objects.all(), 'catalog--discos', 'título', 'musica',
    )


def catalogo_livros(request):
    return _catalogo_response(
        request, 'livros', 'Na prateleira dos livros', 'Sebo · Lombadas',
        Livro.objects.all(), 'catalog--livros', 'título', 'livro',
    )


def catalogo_filmes(request):
    return _catalogo_response(
        request, 'midias', 'Filmes, DVDs e vídeos', 'Cinema · DVD / Blu-ray',
        MidiaAudiovisual.objects.all(), 'catalog--midias', 'título', 'midia',
    )


def home(request):
    musicas = Musica.objects.filter(ativo=True)
    livros = Livro.objects.filter(ativo=True)
    midias = MidiaAudiovisual.objects.filter(ativo=True)
    return render(request, 'loja/home.html', {
        'musicas': musicas,
        'livros': livros,
        'midias': midias,
        'total_musicas': musicas.count(),
        'total_livros': livros.count(),
        'total_midias': midias.count(),
        'ModalidadeComercial': ModalidadeComercial,
    })


def produto_detalhe(request, produto_id):
    ctx = _resolver_produto(produto_id)
    produto = ctx['produto']
    ctx.update({
        'ModalidadeComercial': ModalidadeComercial,
        'pode_venda': produto.disponivel_para(ModalidadeComercial.VENDA),
        'pode_aluguel': produto.disponivel_para(ModalidadeComercial.ALUGUEL),
    })
    return render(request, 'loja/produto_detalhe.html', ctx)


@login_required
def biblioteca(request):
    aba = request.GET.get('aba', 'compras')
    if aba not in ('compras', 'alugueis', 'expirados'):
        aba = 'compras'

    itens = (
        ItemPedido.objects.filter(
            pedido__cliente=request.user,
            pedido__status=Pedido.STATUS_APROVADO,
        )
        .select_related('produto', 'pedido')
        .order_by('-pedido__criado_em')
    )

    compras = []
    alugueis_ativos = []
    expirados = []

    for item in itens:
        entry = {
            'item': item,
            'produto': item.produto,
            'tem_arquivo': item.produto.tem_arquivo,
            'tipo_midia': _tipo_midia_arquivo(item.produto) if item.produto.tem_arquivo else None,
        }
        if item.modalidade == ModalidadeComercial.VENDA:
            compras.append(entry)
        elif item.aluguel_ativo:
            alugueis_ativos.append(entry)
        else:
            expirados.append(entry)

    listas = {
        'compras': compras,
        'alugueis': alugueis_ativos,
        'expirados': expirados,
    }

    return render(request, 'loja/biblioteca.html', {
        'aba': aba,
        'itens_aba': listas[aba],
        'total_compras': len(compras),
        'total_alugueis': len(alugueis_ativos),
        'total_expirados': len(expirados),
    })


@login_required
def reproduzir_conteudo(request, item_id):
    item = get_object_or_404(
        ItemPedido.objects.select_related('produto', 'pedido'),
        pk=item_id,
        pedido__cliente=request.user,
    )
    if not item.acesso_liberado:
        raise Http404('Acesso não disponível.')
    if not item.produto.arquivo:
        raise Http404('Este item não possui arquivo digital.')

    ctx = _resolver_produto(item.produto_id)
    tipo_midia = _tipo_midia_arquivo(item.produto)
    ctx.update({
        'item': item,
        'tipo_midia': tipo_midia,
        'arquivo_url': reverse('acessar_arquivo', args=[item.id]),
    })
    return render(request, 'loja/reproduzir.html', ctx)


@login_required
def acessar_arquivo(request, item_id):
    item = get_object_or_404(
        ItemPedido.objects.select_related('produto', 'pedido'),
        pk=item_id,
        pedido__cliente=request.user,
    )
    if not item.acesso_liberado:
        raise Http404('Acesso não disponível.')
    if not item.produto.arquivo:
        raise Http404('Este item não possui arquivo digital.')

    arquivo = item.produto.arquivo
    return FileResponse(arquivo.open('rb'), as_attachment=False, filename=arquivo.name.split('/')[-1])


def carrinho(request):
    carrinho_data = _get_carrinho(request)
    itens = []
    total = Decimal('0.00')

    for key, entry in list(carrinho_data.items()):
        produto = Produto.objects.filter(pk=entry['produto_id'], ativo=True).first()
        modalidade = entry.get('modalidade', ModalidadeComercial.VENDA)
        quantidade = entry.get('quantidade', 1)
        if not produto or not produto.disponivel_para(modalidade):
            continue
        preco = produto.preco_para(modalidade)
        subtotal = preco * quantidade
        itens.append({
            'key': key,
            'produto': produto,
            'modalidade': modalidade,
            'modalidade_label': dict(ModalidadeComercial.choices).get(modalidade, modalidade),
            'quantidade': quantidade,
            'preco_unitario': preco,
            'dias_aluguel': produto.dias_aluguel if modalidade == ModalidadeComercial.ALUGUEL else None,
            'subtotal': subtotal,
        })
        total += subtotal

    return render(request, 'loja/carrinho.html', {'itens': itens, 'total': total})


@require_POST
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id, ativo=True)
    modalidade = request.POST.get('modalidade', ModalidadeComercial.VENDA)
    if modalidade not in (ModalidadeComercial.VENDA, ModalidadeComercial.ALUGUEL):
        modalidade = ModalidadeComercial.VENDA

    if not produto.disponivel_para(modalidade):
        messages.error(
            request,
            f'"{produto.titulo}" não está disponível para {modalidade}.',
        )
        return redirect('home')

    carrinho = _get_carrinho(request)
    key = f'{produto_id}:{modalidade}'
    atual = carrinho.get(key, {'produto_id': produto_id, 'modalidade': modalidade, 'quantidade': 0})
    nova_qtd = atual.get('quantidade', 0) + 1
    estoque = produto.estoque_para(modalidade)
    if nova_qtd > estoque:
        messages.warning(request, f'Estoque insuficiente para "{produto.titulo}".')
        return redirect('carrinho')

    carrinho[key] = {
        'produto_id': produto_id,
        'modalidade': modalidade,
        'quantidade': nova_qtd,
    }
    _set_carrinho(request, carrinho)
    label = 'aluguel' if modalidade == ModalidadeComercial.ALUGUEL else 'compra'
    messages.success(request, f'"{produto.titulo}" adicionado ao carrinho ({label}).')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('carrinho')


@login_required
@transaction.atomic
def finalizar_pedido(request):
    carrinho = _get_carrinho(request)
    if not carrinho:
        return redirect('carrinho')

    pedido = Pedido.objects.create(cliente=request.user, valor_total=Decimal('0.00'))
    hoje = timezone.localdate()

    for entry in carrinho.values():
        produto = Produto.objects.select_for_update().filter(pk=entry['produto_id'], ativo=True).first()
        modalidade = entry.get('modalidade', ModalidadeComercial.VENDA)
        quantidade = entry.get('quantidade', 1)
        if not produto or not produto.disponivel_para(modalidade):
            continue
        if quantidade > produto.estoque_para(modalidade):
            continue

        dias = produto.dias_aluguel if modalidade == ModalidadeComercial.ALUGUEL else None
        data_devolucao = (hoje + timedelta(days=dias)) if dias else None

        ItemPedido.objects.create(
            pedido=pedido,
            produto=produto,
            modalidade=modalidade,
            quantidade=quantidade,
            preco_unitario=produto.preco_para(modalidade),
            dias_aluguel=dias,
            data_devolucao=data_devolucao,
        )

        if modalidade == ModalidadeComercial.ALUGUEL:
            produto.estoque_aluguel = max(0, produto.estoque_aluguel - quantidade)
            produto.save(update_fields=['estoque_aluguel'])
        else:
            produto.estoque = max(0, produto.estoque - quantidade)
            produto.save(update_fields=['estoque'])

    if not pedido.itens.exists():
        pedido.delete()
        messages.error(request, 'Nenhum item válido no carrinho.')
        return redirect('carrinho')

    pedido.recalcular_valor_total()
    _set_carrinho(request, {})
    return redirect('checkout', pedido_id=pedido.pk)


@login_required
def checkout(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id, cliente=request.user)
    return render(request, 'loja/checkout.html', {
        'pedido': pedido,
        'mercadopago_public_key': settings.MERCADOPAGO_PUBLIC_KEY,
    })


@login_required
def processando_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id, cliente=request.user)
    return render(request, 'loja/processando.html', {'pedido': pedido})


class CriarPreferenciaPagamentoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pedido_id):
        pedido = get_object_or_404(Pedido, pk=pedido_id, cliente=request.user)

        if pedido.status != Pedido.STATUS_AGUARDANDO:
            return Response(
                {'detail': 'Este pedido não está aguardando pagamento.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not pedido.itens.exists():
            return Response(
                {'detail': 'O pedido não possui itens.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pedido.recalcular_valor_total()

        try:
            preference_id = criar_preferencia_pagamento(pedido)
        except MercadoPagoAPIError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            'preference_id': preference_id,
            'public_key': settings.MERCADOPAGO_PUBLIC_KEY,
        })


class PedidoStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pedido_id):
        pedido = get_object_or_404(Pedido, pk=pedido_id, cliente=request.user)

        if settings.DEBUG and pedido.status in (
            Pedido.STATUS_AGUARDANDO,
            Pedido.STATUS_EM_ANALISE,
        ):
            try:
                pedido = sincronizar_pedido_com_mercadopago(pedido)
            except MercadoPagoAPIError:
                logger.warning('Falha ao sincronizar pedido %s com Mercado Pago', pedido.pk)

        return Response({'status': pedido.status, 'pedido_id': pedido.pk})


class MercadoPagoWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not validar_assinatura_webhook(request):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        notification_type = request.data.get('type') or request.GET.get('type')
        data = request.data.get('data') or {}
        payment_id = data.get('id') or request.GET.get('data.id')

        logger.info('Webhook recebido: type=%s payment_id=%s', notification_type, payment_id)

        if notification_type != 'payment' or not payment_id:
            return Response({'detail': 'Notificação ignorada.'})

        try:
            self._processar_pagamento(str(payment_id))
        except MercadoPagoAPIError as exc:
            logger.error('Erro de negócio no webhook: %s', exc)
        except Exception:
            logger.exception('Erro inesperado ao processar webhook payment_id=%s', payment_id)

        return Response({'detail': 'ok'})

    def _processar_pagamento(self, payment_id):
        payment = buscar_pagamento(payment_id)
        external_reference = payment.get('external_reference')
        if not external_reference:
            logger.error('Pagamento %s sem external_reference', payment_id)
            return

        pedido = Pedido.objects.filter(pk=external_reference).first()
        if not pedido:
            logger.error('Pedido %s não encontrado para pagamento %s', external_reference, payment_id)
            return

        aplicar_pagamento_ao_pedido(pedido, payment)
        logger.info('Pagamento %s processado via webhook para pedido %s', payment_id, pedido.pk)


class LoginLojaView(LoginView):
    template_name = 'loja/login.html'


class PasswordResetLojaView(PasswordResetView):
    template_name = 'loja/password_reset.html'
    email_template_name = 'loja/password_reset_email.txt'
    subject_template_name = 'loja/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


class PasswordResetDoneLojaView(PasswordResetDoneView):
    template_name = 'loja/password_reset_done.html'


class PasswordResetConfirmLojaView(PasswordResetConfirmView):
    template_name = 'loja/password_reset_confirm.html'
    success_url = reverse_lazy('login')


class LogoutLojaView(LogoutView):
    next_page = 'home'
