import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Avg, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from .assistant_intent import INTENT_LABELS_CLIENTE, INTENT_LABELS_GESTOR, classify_intent
from .forms_gestao import (
    FraseTreinoForm,
    ImportarCatalogoForm,
    LivroForm,
    MidiaForm,
    MusicaForm,
    PlanoClubeForm,
    TestarIntencaoForm,
)
from .gestao_services import ESTOQUE_BAIXO_LIMITE, gerar_descricao_produto, importar_catalogo_csv, produtos_estoque_baixo
from .models import FraseTreinoAssistente, Livro, MidiaAudiovisual, Musica, Pedido, PlanoClube

logger = logging.getLogger(__name__)


def gestor_required(view_func):
    @wraps(view_func)
    @login_required(login_url='gestao_entrar')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Acesso restrito a gestores da loja.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


class GestaoLoginView(LoginView):
    template_name = 'gestao/entrar.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse('gestao_dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        if not self.request.user.is_staff:
            logout(self.request)
            messages.error(self.request, 'Este usuário não tem permissão de gestão.')
            return redirect('gestao_entrar')
        messages.success(self.request, f'Bem-vindo, {self.request.user.username}.')
        return response


class GestaoLogoutView(LogoutView):
    next_page = reverse_lazy('gestao_entrar')


@gestor_required
def dashboard(request):
    aprovados = Pedido.objects.filter(status=Pedido.STATUS_APROVADO)
    agg = aprovados.aggregate(total=Sum('valor_total'), ticket=Avg('valor_total'))
    return render(request, 'gestao/dashboard.html', {
        'total_discos': Musica.objects.count(),
        'total_livros': Livro.objects.count(),
        'total_midias': MidiaAudiovisual.objects.count(),
        'discos_ativos': Musica.objects.filter(ativo=True).count(),
        'livros_ativos': Livro.objects.filter(ativo=True).count(),
        'midias_ativas': MidiaAudiovisual.objects.filter(ativo=True).count(),
        'pedidos_pendentes': Pedido.objects.filter(
            status__in=[Pedido.STATUS_AGUARDANDO, Pedido.STATUS_EM_ANALISE],
        ).count(),
        'pedidos_aprovados': aprovados.count(),
        'total_vendas': agg['total'] or 0,
        'ticket_medio': agg['ticket'] or 0,
        'ultimos_pedidos': Pedido.objects.select_related('cliente').order_by('-criado_em')[:6],
        'estoque_baixo': produtos_estoque_baixo()[:8],
        'estoque_limite': ESTOQUE_BAIXO_LIMITE,
    })


@gestor_required
def discos_lista(request):
    discos = Musica.objects.order_by('-criado_em')
    return render(request, 'gestao/discos_lista.html', {'discos': discos})


@gestor_required
def disco_criar(request):
    form = MusicaForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, f'Disco "{form.instance.titulo}" cadastrado.')
        return redirect('gestao_discos_lista')
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
    if form.is_valid():
        form.save()
        messages.success(request, f'Disco "{disco.titulo}" atualizado.')
        return redirect('gestao_discos_lista')
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
    if request.method == 'POST':
        titulo = disco.titulo
        disco.delete()
        messages.success(request, f'Disco "{titulo}" removido.')
        return redirect('gestao_discos_lista')
    return render(request, 'gestao/confirmar_exclusao.html', {
        'objeto': disco,
        'tipo': 'disco',
        'voltar_url': 'gestao_discos_lista',
    })


@gestor_required
def livros_lista(request):
    livros = Livro.objects.order_by('-criado_em')
    return render(request, 'gestao/livros_lista.html', {'livros': livros})


@gestor_required
def livro_criar(request):
    form = LivroForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, f'Livro "{form.instance.titulo}" cadastrado.')
        return redirect('gestao_livros_lista')
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
    if form.is_valid():
        form.save()
        messages.success(request, f'Livro "{livro.titulo}" atualizado.')
        return redirect('gestao_livros_lista')
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
    if request.method == 'POST':
        titulo = livro.titulo
        livro.delete()
        messages.success(request, f'Livro "{titulo}" removido.')
        return redirect('gestao_livros_lista')
    return render(request, 'gestao/confirmar_exclusao.html', {
        'objeto': livro,
        'tipo': 'livro',
        'voltar_url': 'gestao_livros_lista',
    })


@gestor_required
def midias_lista(request):
    midias = MidiaAudiovisual.objects.order_by('-criado_em')
    return render(request, 'gestao/midias_lista.html', {'midias': midias})


@gestor_required
def midia_criar(request):
    form = MidiaForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, f'Mídia "{form.instance.titulo}" cadastrada.')
        return redirect('gestao_midias_lista')
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
    if form.is_valid():
        form.save()
        messages.success(request, f'Mídia "{midia.titulo}" atualizada.')
        return redirect('gestao_midias_lista')
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
    if request.method == 'POST':
        titulo = midia.titulo
        midia.delete()
        messages.success(request, f'Mídia "{titulo}" removida.')
        return redirect('gestao_midias_lista')
    return render(request, 'gestao/confirmar_exclusao.html', {
        'objeto': midia,
        'tipo': 'mídia',
        'voltar_url': 'gestao_midias_lista',
    })


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
    pedidos = Pedido.objects.select_related('cliente').prefetch_related('itens').order_by('-criado_em')
    if status:
        pedidos = pedidos.filter(status=status)
    return render(request, 'gestao/pedidos_lista.html', {
        'pedidos': pedidos,
        'filtro_status': status,
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
