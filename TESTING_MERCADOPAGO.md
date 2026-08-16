# Testes manuais — Integração Mercado Pago (Vinil & Página)

## 1. Credenciais de teste (sandbox)

1. Acesse [Mercado Pago Developers](https://www.mercadopago.com.br/developers/panel/app).
2. Crie uma aplicação (ou use uma existente).
3. Em **Credenciais de teste**, copie:
   - **Public Key** → `MERCADOPAGO_PUBLIC_KEY`
   - **Access Token** → `MERCADOPAGO_ACCESS_TOKEN`
4. Em **Webhooks**, configure a URL pública (ver seção 3) e copie o **secret** → `MERCADOPAGO_WEBHOOK_SECRET`.
5. Crie um arquivo `.env` na raiz do projeto (copie de `.env.example`) e preencha as variáveis.

## 2. Cartões de teste

Use estes cartões no Payment Brick (sandbox):

| Cenário   | Número              | CVV | Validade | Nome titular   |
|-----------|---------------------|-----|----------|----------------|
| Aprovado  | 5031 4332 1540 6351 | 123 | 11/30    | APRO           |
| Recusado  | 5031 4332 1540 6351 | 123 | 11/30    | OTHE           |
| Pendente  | 5031 4332 1540 6351 | 123 | 11/30    | CONT           |

Documentação atualizada: [Cartões de teste — Mercado Pago](https://www.mercadopago.com.br/developers/pt/docs/checkout-bricks/additional-content/test-cards).

## 3. Testar webhook localmente (ngrok)

O Mercado Pago precisa de uma URL pública HTTPS para enviar notificações.

1. Inicie o servidor Django:
   ```bash
   python manage.py runserver
   ```
2. Em outro terminal, exponha a porta:
   ```bash
   ngrok http 8000
   ```
3. Copie a URL HTTPS gerada (ex.: `https://abc123.ngrok-free.app`).
4. Atualize o `.env`:
   ```
   SITE_URL=https://abc123.ngrok-free.app
   ```
5. No painel do Mercado Pago, configure o webhook para:
   ```
   https://abc123.ngrok-free.app/api/webhooks/mercadopago/
   ```
6. Reinicie o `runserver` após alterar o `.env`.

## 4. Passo a passo do fluxo completo

- [ ] Criar superusuário: `python manage.py createsuperuser`
- [ ] Popular produtos demo: `python manage.py seed_produtos`
- [ ] Criar usuário de teste (ou usar o admin)
- [ ] Acessar a home, adicionar produtos ao carrinho
- [ ] Fazer login e finalizar o pedido
- [ ] No checkout, pagar com cartão de teste **APRO**
- [ ] Verificar redirecionamento para `/pedidos/<id>/processando/`
- [ ] Aguardar o polling atualizar o status para **Aprovado**
- [ ] Conferir no Django Admin (`/admin/`) se `Pedido` e `Pagamento` foram atualizados

Repita com cartões **OTHE** (recusado) e **CONT** (pendente/em análise).

## 5. Checklist antes de produção

- [ ] `DEBUG=False` em produção
- [ ] `SECRET_KEY` forte e exclusiva
- [ ] HTTPS válido no domínio final
- [ ] Credenciais de **produção** (não sandbox) no `.env`
- [ ] `SITE_URL` apontando para o domínio real (com `https://`)
- [ ] Webhook configurado no painel MP para `https://seudominio.com/api/webhooks/mercadopago/`
- [ ] `back_urls` do checkout apontando para rotas reais do site
- [ ] Banco PostgreSQL em produção (`DATABASE_URL`)
- [ ] Testar um pagamento real de valor baixo antes de abrir ao público

## 6. Testes automatizados

```bash
python manage.py test loja
```
