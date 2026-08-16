"""
Assistente generativo Vinil & Página.
Carrega base de conhecimento (arquivos .md em loja/knowledge/) e usa OpenAI quando configurada.
Pipeline: classificador de intenção (Naive Bayes) → resposta guiada ou LLM com contexto.
"""

import re
from pathlib import Path

from django.conf import settings

from .assistant_intent import (
    CONFIDENCE_THRESHOLD,
    classify_intent,
    response_for_intent,
)
from .models import Livro, Musica

KNOWLEDGE_DIR = Path(__file__).resolve().parent / 'knowledge'


def _load_knowledge_base() -> str:
    if not KNOWLEDGE_DIR.is_dir():
        return ''
    parts = []
    for path in sorted(KNOWLEDGE_DIR.glob('*.md')):
        try:
            parts.append(f'### Arquivo: {path.name}\n{path.read_text(encoding="utf-8")}')
        except OSError:
            continue
    return '\n\n---\n\n'.join(parts)


def _catalog_context(audience: str) -> str:
    total_musicas = Musica.objects.filter(ativo=True).count()
    total_livros = Livro.objects.filter(ativo=True).count()
    musicas = Musica.objects.filter(ativo=True).order_by('titulo')[:12]
    livros = Livro.objects.filter(ativo=True).order_by('titulo')[:12]

    linhas = [
        f'Total discos ativos: {total_musicas}',
        f'Total livros ativos: {total_livros}',
    ]
    if musicas.exists():
        linhas.append('Discos em estoque (amostra):')
        for m in musicas:
            linhas.append(f'- {m.artista} — {m.titulo} | R$ {m.preco} | estoque {m.estoque}')
    if livros.exists():
        linhas.append('Livros em estoque (amostra):')
        for l in livros:
            linhas.append(f'- {l.titulo} — {l.autor} | R$ {l.preco} | estoque {l.estoque}')
    return '\n'.join(linhas)


def _system_prompt(audience: str, intent_info: dict | None = None) -> str:
    knowledge = _load_knowledge_base()
    catalog = _catalog_context(audience)

    if audience == 'gestor':
        role = """
Você é o **Assistente de Gestão** da loja Vinil & Página.
Ajude o gestor a cadastrar discos e livros, escrever descrições, definir preços com bom senso,
organizar o catálogo e entender pedidos/pagamentos.
Responda em português do Brasil. Seja prático e use passos numerados.
Nunca invente funcionalidades que não existem no sistema.
"""
    else:
        role = """
Você é o **Assistente da Loja** Vinil & Página — curadoria de discos e livros.
Ajude o cliente a encontrar produtos, entender como comprar, pagamento e entrega.
Tom acolhedor, como um balconista de loja de discos. Responda em português do Brasil.
Recomende apenas itens do catálogo real listado abaixo. Não invente preços nem estoque.
"""

    intent_block = ''
    if intent_info and intent_info.get('hint') and intent_info.get('confidence', 0) >= 0.3:
        intent_block = (
            f"\n## Intenção detectada: {intent_info['intent']} "
            f"(confiança {intent_info['confidence']:.0%})\n"
            f"{intent_info['hint']}\n"
        )

    return f"""{role}
{intent_block}
## Base de conhecimento (documentos internos)
{knowledge}

## Catálogo atual (dados reais do banco)
{catalog}
"""


CLIENTE_FALLBACKS = [
    (r'como compr|comprar|passo|funciona', 'compra'),
    (r'disco|vinil|música|musica|artista', 'discos'),
    (r'livro|leitura|autor', 'livros'),
    (r'pagamento|pagar|mercado|pix|cartão|cartao', 'pagamento'),
    (r'entrega|frete|correio', 'entrega'),
    (r'recomend|sugere|indica', 'recomendacao'),
]

GESTOR_FALLBACKS = [
    (r'cadastr|novo disco|novo livro|adicionar', 'cadastro'),
    (r'descri|texto|copy', 'descricao'),
    (r'pedido|estoque|preço|preco', 'pedidos_estoque'),
    (r'pagamento|webhook|mercado|pendente', 'pagamento_gestao'),
]

DEFAULT_CLIENTE = (
    'Olá! Sou o assistente da **Vinil & Página**.\n\n'
    'Posso ajudar a escolher discos e livros, explicar como comprar e tirar dúvidas da loja.\n'
    'O que você procura?'
)

DEFAULT_GESTOR = (
    'Olá! Sou o assistente de **gestão** da Vinil & Página.\n\n'
    'Posso ajudar a cadastrar produtos, escrever descrições, organizar o catálogo e entender pedidos.\n'
    'Como posso ajudar?'
)


def _fallback_reply(message: str, audience: str, intent_info: dict | None = None) -> dict:
    if intent_info and intent_info['confidence'] >= CONFIDENCE_THRESHOLD:
        reply = response_for_intent(intent_info['intent'], audience)
        if reply:
            return {
                'reply': reply,
                'source': 'intent',
                'intent': intent_info['intent'],
                'confidence': intent_info['confidence'],
            }

    text = message.lower().strip()
    patterns = GESTOR_FALLBACKS if audience == 'gestor' else CLIENTE_FALLBACKS
    default = DEFAULT_GESTOR if audience == 'gestor' else DEFAULT_CLIENTE
    for pattern, intent_key in patterns:
        if re.search(pattern, text):
            reply = response_for_intent(intent_key, audience) or default
            return {
                'reply': reply,
                'source': 'guided',
                'intent': intent_key,
                'confidence': intent_info['confidence'] if intent_info else 0,
            }

    return {
        'reply': default,
        'source': 'guided',
        'intent': intent_info['intent'] if intent_info else 'geral',
        'confidence': intent_info['confidence'] if intent_info else 0,
    }


def _call_openai(message: str, history: list, audience: str, intent_info: dict) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    messages = [{'role': 'system', 'content': _system_prompt(audience, intent_info)}]
    for item in history[-10:]:
        role = item.get('role', 'user')
        if role in ('user', 'assistant'):
            messages.append({'role': role, 'content': item.get('content', '')})
    messages.append({'role': 'user', 'content': message})

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        temperature=0.55,
        max_tokens=900,
    )
    return response.choices[0].message.content.strip()


def get_greeting(audience: str) -> str:
    ai = 'com IA generativa' if settings.OPENAI_API_KEY else 'com classificador de intenção'
    if audience == 'gestor':
        return (
            f'Olá! Assistente de gestão {ai}.\n\n'
            'Ajudo com cadastro de discos/livros, descrições, catálogo e dúvidas do painel **/gestao/**.\n\n'
            'O que você precisa?'
        )
    return (
        f'Olá! Sou o assistente da loja {ai}.\n\n'
        'Posso recomendar discos e livros, explicar como comprar e tirar dúvidas.\n\n'
        'O que você está procurando?'
    )


def get_suggestions(audience: str) -> list[str]:
    if audience == 'gestor':
        return [
            'Como cadastrar um novo disco?',
            'Me ajude a escrever uma descrição',
            'Como desativar um produto?',
            'O que fazer quando o pagamento fica pendente?',
        ]
    return [
        'Como faço para comprar?',
        'Quais discos vocês têm?',
        'Recomende um livro',
        'Como funciona o pagamento?',
    ]


def chat(message: str, history: list | None = None, audience: str = 'cliente') -> dict:
    message = (message or '').strip()
    if not message:
        return {'error': 'Digite uma mensagem.', 'reply': '', 'source': 'error'}

    audience = 'gestor' if audience == 'gestor' else 'cliente'
    history = history or []
    intent_info = classify_intent(message, audience)

    if settings.OPENAI_API_KEY:
        try:
            reply = _call_openai(message, history, audience, intent_info)
            return {
                'reply': reply,
                'source': 'ai',
                'intent': intent_info['intent'],
                'confidence': intent_info['confidence'],
            }
        except Exception as exc:
            result = _fallback_reply(message, audience, intent_info)
            result['reply'] += f'\n\n_(IA indisponível: {exc}. Resposta orientada local.)_'
            return result

    return _fallback_reply(message, audience, intent_info)
