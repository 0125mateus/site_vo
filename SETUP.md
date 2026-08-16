# Passo a passo — configurar e testar a loja

Siga nesta ordem. O painel `/gestao/` (substituto do admin) será feito depois — por enquanto use o admin só para cadastrar produtos.

---

## 1. Subir o projeto

```powershell
cd "C:\Users\plane\OneDrive\Documentos\projetos cursor\site_vo"
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

## 2. Cadastrar vinis e livros

```powershell
python manage.py createsuperuser
```

1. Acesse **http://localhost:8000/gestao/entrar/**
2. Entre com o usuário criado acima
3. **Discos** → Novo disco → preencha título, artista, preço, estoque e **envie a capa**
4. **Livros** → Novo livro → preencha título, autor, preço, estoque e **envie a capa**

> Não precisa usar `/admin/` — o painel `/gestao/` substitui o admin para o catálogo.

---

## 3. Configurar Mercado Pago no `.env`

1. Abra https://www.mercadopago.com.br/developers/panel/app
2. Crie ou selecione uma aplicação
3. Vá em **Credenciais de teste** e copie:
   - **Public Key** → `MERCADOPAGO_PUBLIC_KEY`
   - **Access Token** → `MERCADOPAGO_ACCESS_TOKEN`
4. Em **Webhooks** (pode fazer no passo 5), copie o **secret** → `MERCADOPAGO_WEBHOOK_SECRET`

Edite o arquivo `.env` na raiz do projeto:

```env
MERCADOPAGO_ACCESS_TOKEN=APP_USR-seu-token-de-teste
MERCADOPAGO_PUBLIC_KEY=APP_USR-sua-public-key-de-teste
MERCADOPAGO_WEBHOOK_SECRET=seu-webhook-secret
SITE_URL=http://localhost:8000
```

Valide as credenciais:

```powershell
python manage.py check_mercadopago
```

Se aparecer **Credenciais OK**, reinicie o `runserver`.

---

## 4. Testar compra (sem webhook ainda)

1. Abra http://localhost:8000
2. Clique em um disco ou livro (vai para o carrinho)
3. Faça login (ou crie usuário em http://localhost:8000/admin/auth/user/add/)
4. **Finalizar pedido** → checkout com Payment Brick
5. Use cartão de teste:

| Campo | Valor |
|-------|-------|
| Número | 5031 4332 1540 6351 |
| CVV | 123 |
| Validade | 11/30 |
| Nome | **APRO** (aprovado) |

O pagamento pode ser aprovado na tela, mas o **status do pedido** só muda automaticamente quando o webhook chegar (passo 5).

---

## 5. Webhook com ngrok (status do pedido automático)

O Mercado Pago precisa de URL pública HTTPS.

**Terminal 1** — servidor:
```powershell
python manage.py runserver
```

**Terminal 2** — ngrok:
```powershell
ngrok http 8000
```

Copie a URL HTTPS (ex.: `https://abc123.ngrok-free.app`) e atualize o `.env`:

```env
SITE_URL=https://abc123.ngrok-free.app
```

No painel Mercado Pago → **Webhooks** → URL:
```
https://abc123.ngrok-free.app/api/webhooks/mercadopago/
```

Reinicie o `runserver` e refaça uma compra de teste.

Confira no admin: **Pedidos** e **Pagamentos** devem mudar para **aprovado**.

---

## 6. Checklist rápido

- [ ] Produtos com capa cadastrados
- [ ] `.env` com credenciais de **teste**
- [ ] `python manage.py check_mercadopago` OK
- [ ] Compra com cartão APRO no checkout
- [ ] ngrok + webhook configurado
- [ ] Status do pedido atualizado após pagamento

---

## Próximo (quando você quiser)

- **Painel `/gestao/`** — cadastrar vinis, livros e imagens sem usar o admin Django
- **Deploy em produção** — HTTPS, PostgreSQL, credenciais reais
