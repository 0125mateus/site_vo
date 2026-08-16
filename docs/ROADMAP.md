# Roadmap — Vinil & Página

Ideias para evoluir a loja e o painel de gestão.

## Gestão (`/gestao/`)

| Prioridade | Feature | Descrição |
|------------|---------|-----------|
| ✅ Feito | Frases de treino do assistente | `/gestao/assistente/` |
| Alta | Lista de pedidos | Ver status, cliente, itens, valor |
| Alta | Gerar descrição com IA | Botão no formulário de disco/livro |
| Média | Dashboard de vendas | Gráfico por período, ticket médio |
| Média | Importar catálogo CSV | Subir muitos itens de uma vez |
| Média | Editar respostas do assistente | Texto exibido por intenção |
| Baixa | Alertas de estoque baixo | E-mail quando estoque &lt; N |
| Baixa | Múltiplos gestores / permissões | Papéis diferentes |

## Loja (cliente)

| Prioridade | Feature | Descrição |
|------------|---------|-----------|
| Alta | Busca e filtros | Por artista, autor, preço, gênero |
| Alta | Página do produto | Detalhes, descrição longa, relacionados |
| Alta | Clube de assinatura | Backend do card "Em breve" |
| Média | Combos livro + disco | Desconto automático |
| Média | Wishlist / favoritos | Salvar para depois |
| Média | Avaliações de clientes | Estrelas + comentário |
| Baixa | Newsletter | Captura de e-mail na home |
| Baixa | Rastreamento de pedido | Código dos Correios |

## Assistente IA

| Prioridade | Feature | Descrição |
|------------|---------|-----------|
| ✅ Feito | Naive Bayes + frases no gestor | `assistant_intent.py` |
| Alta | OpenAI no `.env` | Respostas generativas |
| Média | Busca semântica no catálogo | Embeddings (word2vec / API) |
| Média | Log de conversas | Melhorar treino com dados reais |
| Baixa | Sugestão automática de frases | A partir de chats sem match |

## Pagamentos

| Prioridade | Feature | Descrição |
|------------|---------|-----------|
| Alta | Credenciais MP em produção | `.env` + HTTPS |
| Média | E-mail de confirmação | Após pagamento aprovado |
| Média | Reconciliação Bayesiana | Status incerto → consultar API MP |

## Infra

| Prioridade | Feature | Descrição |
|------------|---------|-----------|
| Alta | Deploy (Render, Railway, VPS) | HTTPS, PostgreSQL |
| Média | CDN para imagens | Cloudinary ou S3 |
| Baixa | CI com testes automáticos | GitHub Actions |

---

*Atualize este arquivo conforme prioridades mudarem.*
