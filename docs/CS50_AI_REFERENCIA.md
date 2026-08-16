# Referência — CS50 AI (Harvard)

Material de estudo local do curso **CS50 — Introdução à Inteligência Artificial com Python** (Harvard).

**Pasta original:** `C:\Users\plane\OneDrive\Desktop\curso ia`

> Não contém código executável — são notas em português e transcrições em inglês (22 arquivos `.txt`).

---

## Mapa das aulas

| Pasta | Aula | Tópico | Arquivo principal (PT) |
|-------|------|--------|------------------------|
| `procurar/` | 0 | Busca (DFS, BFS, A*, Minimax) | `Aula 0.txt` |
| `Conhecimento/` | 1 | Lógica, KB, inferência, CSP | `Novo(a) Documento de Texto.txt` |
| `incerteza/` | 2 | Probabilidade, Bayes, HMM | `Novo(a) Documento de Texto.txt` |
| `otimização/` | 3 | Hill climbing, CSP, scipy | `Novo(a) Documento de Texto.txt` |
| `aprendizagem/` | 4 | ML, sklearn, Q-learning | `Novo(a) Documento de Texto.txt` |
| `redes neurais/` | 5 | TensorFlow/Keras, CNN | `Novo(a) Documento de Texto.txt` |
| `linguagem/` | 6 | NLP, Naive Bayes, Transformers | `Novo(a) Documento de Texto.txt` |

---

## Aplicação no Vinil & Página

| Área do projeto | Aula CS50 | Como usar |
|-----------------|-----------|-----------|
| Assistente de chat | 6 (NLP) | Classificar intenção antes do LLM; RAG com `loja/knowledge/` |
| FAQ determinístico | 1 (Conhecimento) | Regras fixas para frete, pagamento, trocas |
| Webhook Mercado Pago | 2 (Incerteza) | Tratar status como probabilidade; reconciliar com API |
| Recomendação de produtos | 4 (Aprendizagem) | k-NN / clustering no histórico de compras |
| Análise de capas | 5 (Redes neurais) | CNN para classificar qualidade de imagem |
| Busca no catálogo | 0 (Busca) | A* com heurística relevância + estoque |

---

## Evolução sugerida do assistente (híbrido)

```
Pergunta do usuário
    ↓
1. Regras fixas (Aula 1) — FAQ conhecido
    ↓ se não resolver
2. Classificador de intenção (Aula 6 — Naive Bayes)
    ↓
3. LLM + RAG (arquivos .md + catálogo real)
```

---

## Bibliotecas mencionadas no curso

- `nltk` — gramática, n-gramas
- `scikit-learn` — classificação
- `scipy.optimize` — otimização linear
- `tensorflow` / Keras — redes neurais
- `pomegranate` — redes bayesianas

Código oficial do CS50: https://github.com/cs50/ai

---

## Lacunas (complementar fora do curso)

- Django, REST, PostgreSQL
- Mercado Pago SDK e webhooks
- APIs OpenAI / Anthropic, vector DB (pgvector)
- Deploy e segurança

---

## Para outros projetos

| Tipo de projeto | Aulas mais úteis |
|-----------------|------------------|
| Chatbot / suporte | 1, 6 |
| E-commerce / pagamentos | 2, 4 |
| Logística / rotas | 0, 3 |
| Classificação / fraude | 4, 5 |
| Imagens / visão | 5 |

---

*Índice criado em jul/2026 para consulta pelo Cursor e pela equipe.*
