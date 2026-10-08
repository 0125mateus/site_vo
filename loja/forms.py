import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Pedido

User = get_user_model()

UFS = (
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
    'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
)


class EnderecoEntregaForm(forms.ModelForm):
    entrega_uf = forms.ChoiceField(
        label='Estado',
        choices=[('', 'UF')] + [(uf, uf) for uf in UFS],
    )

    class Meta:
        model = Pedido
        fields = Pedido.CAMPOS_ENTREGA
        widgets = {
            'entrega_nome': forms.TextInput(attrs={'autocomplete': 'name'}),
            'entrega_telefone': forms.TextInput(attrs={
                'autocomplete': 'tel', 'inputmode': 'tel', 'placeholder': '(11) 99999-9999',
            }),
            'entrega_cep': forms.TextInput(attrs={
                'autocomplete': 'postal-code', 'inputmode': 'numeric', 'placeholder': '00000-000',
                'data-cep': '1',
            }),
            'entrega_logradouro': forms.TextInput(attrs={'autocomplete': 'address-line1'}),
            'entrega_numero': forms.TextInput(attrs={'inputmode': 'numeric'}),
            'entrega_complemento': forms.TextInput(attrs={
                'autocomplete': 'address-line2', 'placeholder': 'Apto, bloco… (opcional)',
            }),
            'entrega_bairro': forms.TextInput(),
            'entrega_cidade': forms.TextInput(attrs={'autocomplete': 'address-level2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            campo.required = nome != 'entrega_complemento'

    def clean_entrega_cep(self):
        digitos = re.sub(r'\D', '', self.cleaned_data.get('entrega_cep') or '')
        if len(digitos) != 8:
            raise forms.ValidationError('O CEP tem 8 números.')
        return f'{digitos[:5]}-{digitos[5:]}'

    def clean_entrega_telefone(self):
        telefone = (self.cleaned_data.get('entrega_telefone') or '').strip()
        if len(re.sub(r'\D', '', telefone)) < 10:
            raise forms.ValidationError('Informe o telefone com DDD.')
        return telefone


class RegistroClienteForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'auth-input',
            'placeholder': ' ',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('username', 'password1', 'password2'):
            self.fields[name].widget.attrs.update({
                'class': 'auth-input',
                'placeholder': ' ',
            })
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
