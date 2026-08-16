from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy

from .assistant_intent import INTENT_LABELS_CLIENTE, INTENT_LABELS_GESTOR, classify_intent
from .forms_gestao import FraseTreinoForm, LivroForm, MidiaForm, MusicaForm, TestarIntencaoForm
from .models import FraseTreinoAssistente, Livro, MidiaAudiovisual, Musica, Pedido


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
