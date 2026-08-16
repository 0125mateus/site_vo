# Teste de compra — Mercado Pago (passo a passo)

## 1. Obter credenciais sandbox

1. Acesse https://www.mercadopago.com.br/developers/panel/app
2. Crie uma aplicação (tipo: Checkout / Pagamentos online)
3. Vá em **Credenciais de teste**
4. Copie:
   - **Public Key** (começa com `APP_USR-` ou `TEST-`)
   - **Access Token** (começa com `APP_USR-` ou `TEST-`)

## 2. Editar o `.env`

Abra o arquivo `.env` na raiz do projeto:

```env
MERCADOPAGO_ACCESS_TOKEN=APP_USR-cole-seu-token-de-teste-aqui
MERCADOPAGO_PUBLIC_KEY=APP_USR-cole-sua-public-key-de-teste-aqui
MERCADOPAGO_WEBHOOK_SECRET=
SITE_URL=http://localhost:8000
```

> O `WEBHOOK_SECRET` pode ficar vazio para o primeiro teste.
> Em modo DEBUG, o status do pedido é sincronizado pela API do MP na página de processamento (sem ngrok).

## 3. Validar

```powershell
cd "C:\Users\plane\OneDrive\Documentos\projetos cursor\site_vo"
python manage.py check_mercadopago
python manage.py preparar_teste_compra
```

## 4. Subir o servidor

```powershell
python manage.py runserver
```

## 5. Fazer a compra de teste

| Passo | Ação |
|-------|------|
| 1 | http://localhost:8000 — clique em um produto |
| 2 | Carrinho → login **comprador** / **comprador123** |
| 3 | Finalizar pedido |
| 4 | Preencha o cartão de teste (abaixo) |
| 5 | Aguarde na página de processamento |

### Cartão de teste — pagamento APROVADO

| Campo | Valor |
|-------|-------|
| Número | `5031 4332 1540 6351` |
| CVV | `123` |
| Validade | `11/30` |
| Nome no cartão | `APRO` |

Outros cenários: nome **OTHE** (recusado), **CONT** (pendente).

## 6. Webhook (para status automático do pedido)

Sem webhook, o Brick aprova na tela mas o pedido pode ficar "aguardando pagamento".

1. Instale ngrok: https://ngrok.com/download
2. `ngrok http 8000`
3. Copie a URL HTTPS (ex.: `https://abc123.ngrok-free.app`)
4. No `.env`: `SITE_URL=https://abc123.ngrok-free.app`
5. No painel MP → Webhooks → URL: `https://abc123.ngrok-free.app/api/webhooks/mercadopago/`
6. Copie o **secret** para `MERCADOPAGO_WEBHOOK_SECRET`
7. Reinicie o `runserver`

## 7. Conferir resultado

- Loja: página de processamento mostra status
- Gestão: http://localhost:8000/gestao/ — pedidos pendentes no resumo

## Problemas comuns

| Erro | Solução |
|------|---------|
| Payment Brick não carrega | `MERCADOPAGO_PUBLIC_KEY` vazio ou inválido |
| Erro 502 no checkout | `MERCADOPAGO_ACCESS_TOKEN` inválido |
| Status não muda | Configure webhook com ngrok |
| `check_mercadopago` falha | Use credenciais de **teste**, não produção |
