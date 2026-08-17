"""Serviços auxiliares do painel de gestão."""

import csv
import io
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings

from .models import Livro, Musica, Produto

logger = logging.getLogger(__name__)

ESTOQUE_BAIXO_LIMITE = 3


def produtos_estoque_baixo():
    """Produtos ativos com estoque de venda ou aluguel abaixo do limite."""
    alertas = []
    for produto in Produto.objects.filter(ativo=True).order_by('titulo'):
        if produto.disponivel_venda and 0 < produto.estoque <= ESTOQUE_BAIXO_LIMITE:
            alertas.append({'produto': produto, 'tipo': 'venda', 'estoque': produto.estoque})
        if produto.disponivel_aluguel and 0 < produto.estoque_aluguel <= ESTOQUE_BAIXO_LIMITE:
            alertas.append({'produto': produto, 'tipo': 'aluguel', 'estoque': produto.estoque_aluguel})
    return alertas


def gerar_descricao_produto(titulo: str, tipo: str, extra: str = '') -> str:
    if not settings.OPENAI_API_KEY:
        raise ValueError('OpenAI não configurada. Defina OPENAI_API_KEY no ambiente.')

    from openai import OpenAI

    tipo_label = {'disco': 'disco de vinil', 'livro': 'livro', 'midia': 'filme ou DVD'}.get(tipo, 'item')
    prompt = (
        f'Escreva uma descrição curta e convidativa (2–4 frases, tom de sebo/disqueira) '
        f'para um {tipo_label} intitulado "{titulo}".'
    )
    if extra:
        prompt += f' Informações extras: {extra}.'
    prompt += ' Responda só com o texto da descrição, em português do Brasil.'

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {'role': 'system', 'content': 'Você escreve textos de catálogo para a loja Vinil & Página.'},
            {'role': 'user', 'content': prompt},
        ],
        max_tokens=280,
        temperature=0.7,
    )
    return (response.choices[0].message.content or '').strip()


def importar_catalogo_csv(arquivo) -> dict:
    """
    CSV: tipo,titulo,preco[,artista|autor][,estoque]
    tipo = disco|livro
    """
    conteudo = arquivo.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(conteudo))
    criados = 0
    erros = []

    for linha, row in enumerate(reader, start=2):
        tipo = (row.get('tipo') or '').strip().lower()
        titulo = (row.get('titulo') or '').strip()
        if not titulo:
            erros.append(f'Linha {linha}: título vazio.')
            continue
        try:
            preco = Decimal(str(row.get('preco', '0')).replace(',', '.'))
        except (InvalidOperation, TypeError):
            erros.append(f'Linha {linha}: preço inválido.')
            continue
        estoque = int(row.get('estoque') or 1)

        if tipo in ('disco', 'musica', 'vinil'):
            artista = (row.get('artista') or 'Artista').strip()
            Musica.objects.create(
                titulo=titulo,
                artista=artista,
                preco=preco,
                estoque=estoque,
                disponivel_venda=True,
                ativo=True,
            )
            criados += 1
        elif tipo == 'livro':
            autor = (row.get('autor') or 'Autor').strip()
            Livro.objects.create(
                titulo=titulo,
                autor=autor,
                preco=preco,
                estoque=estoque,
                disponivel_venda=True,
                ativo=True,
            )
            criados += 1
        else:
            erros.append(f'Linha {linha}: tipo "{tipo}" inválido (use disco ou livro).')

    return {'criados': criados, 'erros': erros}
