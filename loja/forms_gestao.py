from django import forms

from .assistant_intent import get_intent_choices
import re

from .models import (
    ConfiguracaoPix, FraseTreinoAssistente, Livro, MidiaAudiovisual, Musica, Pedido, PlanoClube,
)


class EntregaPedidoForm(forms.ModelForm):
    mensagem = forms.CharField(
        label='Recado para o cliente', required=False, max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Opcional. Ex.: Previsão de chegada em 5 dias úteis'}),
    )

    class Meta:
        model = Pedido
        fields = ['status_entrega', 'transportadora', 'codigo_rastreio', 'link_rastreio']
        widgets = {
            'transportadora': forms.TextInput(attrs={'placeholder': 'Ex.: Correios, Jadlog, motoboy'}),
            'codigo_rastreio': forms.TextInput(attrs={'placeholder': 'Ex.: AA123456789BR'}),
            'link_rastreio': forms.URLInput(attrs={'placeholder': 'Opcional: link da transportadora'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status_entrega'].required = True
        self.fields['status_entrega'].choices = Pedido.StatusEntrega.choices

    def clean_codigo_rastreio(self):
        return (self.cleaned_data.get('codigo_rastreio') or '').strip().upper()


class ConfiguracaoPixForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoPix
        fields = ['tipo_chave', 'chave', 'nome_recebedor', 'cidade']
        widgets = {
            'chave': forms.TextInput(attrs={'placeholder': 'A chave cadastrada no seu banco'}),
            'nome_recebedor': forms.TextInput(attrs={'placeholder': 'Ex.: Mateus Pereira'}),
            'cidade': forms.TextInput(attrs={'placeholder': 'Ex.: Belo Horizonte'}),
        }

    def clean(self):
        dados = super().clean()
        tipo = dados.get('tipo_chave')
        chave = (dados.get('chave') or '').strip()
        digitos = re.sub(r'\D', '', chave)
        erro = None
        if tipo == ConfiguracaoPix.TipoChave.CPF and len(digitos) != 11:
            erro = 'O CPF tem 11 números.'
        elif tipo == ConfiguracaoPix.TipoChave.CNPJ and len(digitos) != 14:
            erro = 'O CNPJ tem 14 números.'
        elif tipo == ConfiguracaoPix.TipoChave.TELEFONE and not 10 <= len(digitos) <= 13:
            erro = 'Informe o celular com DDD, como está cadastrado no banco.'
        elif tipo == ConfiguracaoPix.TipoChave.EMAIL and '@' not in chave:
            erro = 'Informe o e-mail cadastrado como chave.'
        elif tipo == ConfiguracaoPix.TipoChave.ALEATORIA and len(chave) != 36:
            erro = 'A chave aleatória tem 36 caracteres, com tracinhos.'
        if erro:
            self.add_error('chave', erro)
        return dados


class MusicaForm(forms.ModelForm):
    class Meta:
        model = Musica
        fields = [
            'titulo', 'artista', 'formato', 'descricao',
            'imagem', 'arquivo',
            'disponivel_venda', 'preco', 'estoque',
            'disponivel_aluguel', 'preco_aluguel', 'dias_aluguel', 'estoque_aluguel',
            'ativo',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Ex.: Abbey Road'}),
            'artista': forms.TextInput(attrs={'placeholder': 'Ex.: The Beatles'}),
            'formato': forms.TextInput(attrs={'placeholder': 'vinil, CD, MP3…'}),
            'descricao': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Descrição opcional'}),
            'preco': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'preco_aluguel': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'dias_aluguel': forms.NumberInput(attrs={'min': '1'}),
            'estoque': forms.NumberInput(attrs={'min': '0'}),
            'estoque_aluguel': forms.NumberInput(attrs={'min': '0'}),
            'arquivo': forms.ClearableFileInput(attrs={
                'accept': 'audio/*,.mp3,.flac,.wav,.aac,.m4a,.ogg',
            }),
            'imagem': forms.ClearableFileInput(attrs={
                'accept': 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp',
            }),
        }


class LivroForm(forms.ModelForm):
    class Meta:
        model = Livro
        fields = [
            'titulo', 'autor', 'isbn', 'descricao',
            'imagem', 'arquivo',
            'disponivel_venda', 'preco', 'estoque',
            'disponivel_aluguel', 'preco_aluguel', 'dias_aluguel', 'estoque_aluguel',
            'ativo',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Ex.: 1984'}),
            'autor': forms.TextInput(attrs={'placeholder': 'Ex.: George Orwell'}),
            'isbn': forms.TextInput(attrs={'placeholder': 'Opcional'}),
            'descricao': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Descrição opcional'}),
            'preco': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'preco_aluguel': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'dias_aluguel': forms.NumberInput(attrs={'min': '1'}),
            'estoque': forms.NumberInput(attrs={'min': '0'}),
            'estoque_aluguel': forms.NumberInput(attrs={'min': '0'}),
            'arquivo': forms.ClearableFileInput(attrs={
                'accept': '.pdf,.epub,.mobi,application/pdf',
            }),
            'imagem': forms.ClearableFileInput(attrs={
                'accept': 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp',
            }),
        }


class MidiaForm(forms.ModelForm):
    class Meta:
        model = MidiaAudiovisual
        fields = [
            'titulo', 'tipo', 'diretor', 'ano', 'duracao_min', 'descricao',
            'imagem', 'trailer', 'trailer_url', 'arquivo',
            'disponivel_assistir', 'preco_assistir', 'filme_url',
            'disponivel_venda', 'preco', 'estoque',
            'ativo',
        ]
        labels = {
            'disponivel_assistir': 'Vender para assistir online',
            'preco_assistir': 'Preço para assistir (R$)',
            'disponivel_venda': 'Vender o DVD físico',
            'preco': 'Preço do DVD (R$)',
            'estoque': 'DVDs em estoque',
        }
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Ex.: O Poderoso Chefão'}),
            'tipo': forms.Select(),
            'diretor': forms.TextInput(attrs={'placeholder': 'Ex.: Francis Ford Coppola'}),
            'ano': forms.NumberInput(attrs={'min': '1900', 'max': '2100', 'placeholder': '1972'}),
            'duracao_min': forms.NumberInput(attrs={'min': '1', 'placeholder': '175'}),
            'descricao': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Sinopse ou detalhes'}),
            'preco': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'preco_assistir': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'estoque': forms.NumberInput(attrs={'min': '0'}),
            'filme_url': forms.URLInput(attrs={
                'placeholder': 'https://youtu.be/… ou https://drive.google.com/file/d/…',
            }),
            'trailer': forms.ClearableFileInput(attrs={
                'accept': 'video/mp4,video/webm,video/ogg,.mp4,.webm,.ogg',
            }),
            'trailer_url': forms.URLInput(attrs={
                'placeholder': 'https://www.youtube.com/watch?v=…',
            }),
            'arquivo': forms.ClearableFileInput(attrs={
                'accept': 'video/*,.mp4,.mkv,.avi,.mov,.wmv,.iso',
            }),
            'imagem': forms.ClearableFileInput(attrs={
                'accept': 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp',
                'data-capa-vertical': '1',
            }),
        }

    CAMPOS_OPCIONAIS_ZERO = ('preco_assistir', 'preco', 'estoque')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome in self.CAMPOS_OPCIONAIS_ZERO:
            self.fields[nome].required = False

    def clean(self):
        dados = super().clean()
        for nome in self.CAMPOS_OPCIONAIS_ZERO:
            if dados.get(nome) is None and nome not in self.errors:
                dados[nome] = 0
        if dados.get('disponivel_assistir'):
            if not dados.get('preco_assistir') or dados['preco_assistir'] <= 0:
                self.add_error('preco_assistir', 'Informe quanto custa para assistir online.')
            if not dados.get('filme_url') and not dados.get('arquivo'):
                self.add_error('filme_url', 'Coloque o link do filme completo para quem pagar conseguir assistir.')
        if dados.get('disponivel_venda') and (not dados.get('preco') or dados['preco'] <= 0):
            self.add_error('preco', 'Informe o preço do DVD físico.')
        return dados


class FraseTreinoForm(forms.ModelForm):
    class Meta:
        model = FraseTreinoAssistente
        fields = ['audiencia', 'intencao', 'texto', 'ativo']
        widgets = {
            'texto': forms.TextInput(attrs={
                'placeholder': 'Ex.: como faço para comprar com pix?',
            }),
        }

    def __init__(self, *args, audiencia=None, **kwargs):
        super().__init__(*args, **kwargs)
        aud = audiencia or self.initial.get('audiencia') or FraseTreinoAssistente.AUDIENCIA_CLIENTE
        self.fields['intencao'].widget = forms.Select(
            choices=get_intent_choices(aud),
        )
        if audiencia:
            self.fields['audiencia'].widget = forms.HiddenInput()
            self.fields['audiencia'].initial = audiencia


class TestarIntencaoForm(forms.Form):
    audiencia = forms.ChoiceField(
        choices=FraseTreinoAssistente.AUDIENCIA_CHOICES,
        initial=FraseTreinoAssistente.AUDIENCIA_CLIENTE,
    )
    mensagem = forms.CharField(
        max_length=300,
        widget=forms.TextInput(attrs={'placeholder': 'Digite uma frase para testar…'}),
    )


class PlanoClubeForm(forms.ModelForm):
    class Meta:
        model = PlanoClube
        fields = [
            'titulo', 'descricao', 'preco_mensal', 'desconto_extra_percent', 'ativo', 'ordem',
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'preco_mensal': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }


class ImportarCatalogoForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo CSV',
        help_text='Colunas: tipo,titulo,preco,artista|autor,estoque',
    )


class AcessoClienteForm(forms.Form):
    nova_senha = forms.CharField(
        label='Nova senha',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    confirmar_senha = forms.CharField(
        label='Confirmar nova senha',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean(self):
        dados = super().clean()
        senha = dados.get('nova_senha') or ''
        confirma = dados.get('confirmar_senha') or ''
        if senha and confirma and senha != confirma:
            self.add_error('confirmar_senha', 'A confirmação não confere com a nova senha.')
            return dados
        if not senha:
            return dados
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        try:
            validate_password(senha, self.usuario)
        except ValidationError as exc:
            self.add_error('nova_senha', exc)
        return dados

    def salvar(self):
        self.usuario.set_password(self.cleaned_data['nova_senha'])
        self.usuario.save(update_fields=['password'])
