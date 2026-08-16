"""
Classificador de intenção — Naive Bayes + Bag-of-Words (CS50 AI, Aula 6).
Treino: frases padrão + frases cadastradas no painel /gestao/assistente/
"""

from __future__ import annotations

import copy

# Frases padrão (sempre incluídas; edite aqui ou adicione pelo painel)
TRAINING_CLIENTE: dict[str, list[str]] = {
    'compra': [
        'como faço para comprar',
        'como comprar um disco',
        'passo a passo da compra',
        'como funciona a loja',
        'quero comprar um livro',
        'como adiciono ao carrinho',
        'como finalizar pedido',
        'processo de compra',
        'onde clico para comprar',
        'como fechar pedido',
        'preciso criar conta',
        'como usar o carrinho',
    ],
    'discos': [
        'quais discos vocês têm',
        'tem vinil de jazz',
        'mostre os discos',
        'prateleira de discos',
        'vinil do beatles',
        'música disponível',
        'artista na loja',
        'catálogo de vinil',
        'tem lp de rock',
        'discos em estoque',
        'vinil nacional',
        'álbum disponível',
    ],
    'livros': [
        'quais livros tem',
        'recomende um livro',
        'autor disponível',
        'prateleira de livros',
        'livro de ficção',
        'quero ler algo bom',
        'romance na loja',
        'tem livro de poesia',
        'biografia disponível',
        'literatura brasileira',
    ],
    'pagamento': [
        'como pago',
        'aceita pix',
        'mercado pago',
        'cartão de crédito',
        'formas de pagamento',
        'como funciona o pagamento',
        'pagar com pix',
        'parcela no cartão',
        'boleto',
        'pagamento recusado',
        'deu erro no pagamento',
    ],
    'entrega': [
        'como é a entrega',
        'enviam pelos correios',
        'prazo de entrega',
        'frete',
        'quando chega o pedido',
        'quanto custa o envio',
        'entrega para minha cidade',
        'rastreio do pedido',
    ],
    'recomendacao': [
        'me recomenda algo',
        'o que você sugere',
        'indica um disco',
        'presente para quem gosta de música',
        'combo livro e disco',
        'surpreenda me com um vinil',
        'algo para presentear',
        'o que está em alta',
    ],
}

TRAINING_GESTOR: dict[str, list[str]] = {
    'cadastro': [
        'como cadastrar disco',
        'novo livro no sistema',
        'adicionar produto',
        'cadastrar vinil',
        'criar item no catálogo',
        'incluir música na loja',
        'subir capa do produto',
        'publicar novo item',
        'incluir álbum',
    ],
    'descricao': [
        'ajude com a descrição',
        'escrever texto do produto',
        'rascunho de copy',
        'como descrever o disco',
        'texto para a capa',
        'melhorar descrição',
        'gerar sinopse do livro',
        'texto de venda',
    ],
    'pedidos_estoque': [
        'atualizar estoque',
        'editar preço',
        'pedidos pendentes',
        'desativar produto',
        'quantidade em estoque',
        'preço do livro',
        'esgotou o disco',
        'ocultar da loja',
        'ver pedidos',
    ],
    'pagamento_gestao': [
        'pagamento pendente',
        'webhook mercado pago',
        'pedido não aprovou',
        'status do pagamento',
        'mercadopago não atualizou',
        'configurar credenciais mp',
        'testar mercado pago',
        'pagamento em análise',
    ],
}

INTENT_LABELS_CLIENTE = {
    'compra': 'Como comprar',
    'discos': 'Discos / vinil',
    'livros': 'Livros',
    'pagamento': 'Pagamento',
    'entrega': 'Entrega / frete',
    'recomendacao': 'Recomendação',
}

INTENT_LABELS_GESTOR = {
    'cadastro': 'Cadastro de produto',
    'descricao': 'Descrição / copy',
    'pedidos_estoque': 'Pedidos e estoque',
    'pagamento_gestao': 'Pagamento / Mercado Pago',
}

INTENT_RESPONSES_CLIENTE: dict[str, str] = {
    'compra': (
        'Para comprar na Vinil & Página:\n\n'
        '1. Clique em um disco ou livro na prateleira\n'
        '2. Vá ao **carrinho** e faça login\n'
        '3. **Finalize o pedido** e pague com Mercado Pago\n\n'
        'Quer ajuda para escolher algo?'
    ),
    'discos': (
        'Nossa prateleira de **discos** está na home.\n'
        'Cada capa mostra título, artista e preço — clique para adicionar ao carrinho.\n\n'
        'Me diga um artista ou gênero que eu ajudo a escolher!'
    ),
    'livros': (
        'Os **livros** aparecem como lombadas na segunda prateleira.\n'
        'Clique para adicionar ao carrinho.\n\n'
        'Posso sugerir algo se você disser um autor ou tema!'
    ),
    'pagamento': (
        'O pagamento é pelo **Mercado Pago** no checkout (cartão, Pix, etc.).\n'
        'Após pagar, acompanhe o status na página de processamento.'
    ),
    'entrega': (
        'Enviamos pelos **Correios** conforme disponibilidade.\n'
        'Prazos e valores dependem do pedido — confira no checkout.'
    ),
    'recomendacao': (
        'Conte o que você curte — jazz, rock, ficção, biografia — '
        'e eu sugiro discos ou livros do nosso catálogo atual.'
    ),
}

INTENT_RESPONSES_GESTOR: dict[str, str] = {
    'cadastro': (
        'No painel **/gestao/**:\n\n'
        '**Disco:** Discos → Novo disco\n'
        '**Livro:** Livros → Novo livro\n\n'
        'Preencha título, preço, estoque e envie a **capa**. Marque **ativo** para publicar.'
    ),
    'descricao': (
        'Boas descrições: gênero/tema, por que está na curadoria, detalhes da edição.\n'
        'Me diga título e artista/autor que rascunho um texto para você revisar.'
    ),
    'pedidos_estoque': (
        'Em **/gestao/** → Discos ou Livros → Editar.\n'
        'Ajuste preço e estoque; desmarque **ativo** para ocultar da loja.'
    ),
    'pagamento_gestao': (
        'Pagamentos passam pelo Mercado Pago. Se o status não atualizar:\n'
        '1. Confira `SITE_URL` e webhook no painel MP\n'
        '2. Rode `python manage.py check_mercadopago`\n'
        '3. Veja pedidos no resumo do painel de gestão'
    ),
}

INTENT_HINTS: dict[str, str] = {
    'compra': 'O usuário quer saber como comprar na loja.',
    'discos': 'O usuário busca discos/vinil no catálogo.',
    'livros': 'O usuário busca livros no catálogo.',
    'pagamento': 'Dúvida sobre pagamento (Mercado Pago, Pix, cartão).',
    'entrega': 'Dúvida sobre entrega e frete.',
    'recomendacao': 'Pedido de recomendação personalizada.',
    'cadastro': 'Gestor quer cadastrar produto no painel.',
    'descricao': 'Gestor quer ajuda com texto/descrição de produto.',
    'pedidos_estoque': 'Gestor quer gerir pedidos, preço ou estoque.',
    'pagamento_gestao': 'Gestor com dúvida sobre pagamento/webhook MP.',
}

CONFIDENCE_THRESHOLD = 0.45

_model_cache: dict[str, tuple] = {}


def get_intent_choices(audiencia: str) -> list[tuple[str, str]]:
    labels = INTENT_LABELS_GESTOR if audiencia == 'gestor' else INTENT_LABELS_CLIENTE
    return list(labels.items())


def invalidate_model_cache():
    _model_cache.clear()


def _training_from_db(audiencia: str) -> dict[str, list[str]]:
    from .models import FraseTreinoAssistente

    extra: dict[str, list[str]] = {}
    for frase in FraseTreinoAssistente.objects.filter(audiencia=audiencia, ativo=True):
        extra.setdefault(frase.intencao, []).append(frase.texto.lower().strip())
    return extra


def get_merged_training(audiencia: str) -> dict[str, list[str]]:
    base = copy.deepcopy(TRAINING_GESTOR if audiencia == 'gestor' else TRAINING_CLIENTE)
    for intent, frases in _training_from_db(audiencia).items():
        if intent in base:
            base[intent].extend(frases)
        else:
            base[intent] = frases
    return base


def _build_training(audiencia: str) -> tuple[list[str], list[str]]:
    data = get_merged_training(audiencia)
    texts, labels = [], []
    for intent, examples in data.items():
        for text in examples:
            text = text.strip().lower()
            if text:
                texts.append(text)
                labels.append(intent)
    return texts, labels


def _get_model(audiencia: str):
    if audiencia in _model_cache:
        return _model_cache[audiencia]

    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.naive_bayes import MultinomialNB

    texts, labels = _build_training(audiencia)
    if not texts:
        return None, None

    vectorizer = CountVectorizer(lowercase=True, ngram_range=(1, 2))
    X = vectorizer.fit_transform(texts)
    classifier = MultinomialNB(alpha=0.1)
    classifier.fit(X, labels)
    _model_cache[audiencia] = (vectorizer, classifier)
    return vectorizer, classifier


def classify_intent(message: str, audience: str = 'cliente') -> dict:
    audience = 'gestor' if audience == 'gestor' else 'cliente'
    message = (message or '').strip().lower()

    if not message:
        return {'intent': 'geral', 'confidence': 0.0, 'hint': ''}

    try:
        vectorizer, classifier = _get_model(audience)
        if vectorizer is None:
            return {'intent': 'geral', 'confidence': 0.0, 'hint': ''}

        X = vectorizer.transform([message])
        intent = classifier.predict(X)[0]
        proba = classifier.predict_proba(X)[0]
        classes = list(classifier.classes_)
        confidence = float(proba[classes.index(intent)])
        hint = INTENT_HINTS.get(intent, '')
        return {
            'intent': intent,
            'confidence': round(confidence, 3),
            'hint': hint,
        }
    except Exception:
        return {'intent': 'geral', 'confidence': 0.0, 'hint': ''}


def response_for_intent(intent: str, audience: str) -> str | None:
    responses = INTENT_RESPONSES_GESTOR if audience == 'gestor' else INTENT_RESPONSES_CLIENTE
    return responses.get(intent)
