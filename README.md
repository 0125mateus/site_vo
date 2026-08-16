# Vinil & Página

Loja de discos e livros em Django + DRF com integração Mercado Pago (Payment Brick).

## Setup rápido

Guia completo: **[SETUP.md](SETUP.md)** (cadastro de produtos, Mercado Pago, teste de compra).

```bash
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_produtos
python manage.py runserver
```

Acesse: http://localhost:8000

## Variáveis de ambiente

Veja `.env.example`. Para testes com Mercado Pago, preencha as credenciais sandbox.

## Documentação de testes

Consulte `TESTING_MERCADOPAGO.md` para o checklist completo de testes manuais e webhook.
