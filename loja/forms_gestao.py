from django import forms

from .assistant_intent import get_intent_choices
from .models import FraseTreinoAssistente, Livro, MidiaAudiovisual, Musica


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
        }


class MidiaForm(forms.ModelForm):
    class Meta:
        model = MidiaAudiovisual
        fields = [
            'titulo', 'tipo', 'diretor', 'ano', 'duracao_min', 'descricao',
            'imagem', 'trailer', 'trailer_url', 'arquivo',
            'disponivel_venda', 'preco', 'estoque',
            'disponivel_aluguel', 'preco_aluguel', 'dias_aluguel', 'estoque_aluguel',
            'ativo',
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Ex.: O Poderoso Chefão'}),
            'tipo': forms.Select(),
            'diretor': forms.TextInput(attrs={'placeholder': 'Ex.: Francis Ford Coppola'}),
            'ano': forms.NumberInput(attrs={'min': '1900', 'max': '2100', 'placeholder': '1972'}),
            'duracao_min': forms.NumberInput(attrs={'min': '1', 'placeholder': '175'}),
            'descricao': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Sinopse ou detalhes'}),
            'preco': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'preco_aluguel': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'dias_aluguel': forms.NumberInput(attrs={'min': '1'}),
            'estoque': forms.NumberInput(attrs={'min': '0'}),
            'estoque_aluguel': forms.NumberInput(attrs={'min': '0'}),
            'trailer': forms.ClearableFileInput(attrs={
                'accept': 'video/mp4,video/webm,video/ogg,.mp4,.webm,.ogg',
            }),
            'trailer_url': forms.URLInput(attrs={
                'placeholder': 'https://www.youtube.com/watch?v=…',
            }),
            'arquivo': forms.ClearableFileInput(attrs={
                'accept': 'video/*,.mp4,.mkv,.avi,.mov,.wmv,.iso',
            }),
        }


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
