# Gestão do catálogo — painel /gestao/

## Acesso
- URL: `/gestao/entrar/`
- Usuário com permissão de **gestor** (staff).
- Criar gestor: `python manage.py criar_gestor`

## Cadastrar disco
1. Gestão → **Discos** → **Novo disco**
2. Preencher: título, artista, formato, descrição, preço, estoque
3. Enviar **capa** (JPG/PNG/WebP)
4. Marcar **ativo** para aparecer na loja

## Cadastrar livro
1. Gestão → **Livros** → **Novo livro**
2. Preencher: título, autor, ISBN (opcional), descrição, preço, estoque
3. Enviar **capa**
4. Marcar **ativo**

## Editar e desativar
- **Editar** atualiza qualquer campo; nova imagem substitui a anterior.
- Desmarcar **ativo** remove da loja sem apagar o registro.
- **Excluir** remove permanentemente.

## Pedidos
- Pedidos pendentes aparecem no resumo do painel.
- Status: aguardando pagamento, em análise, aprovado, recusado.
- Detalhes de pagamento via integração Mercado Pago (webhook).

## Boas práticas do gestor
- Mantenha estoque atualizado após cada venda manual ou conferência.
- Revise descrições periodicamente — SEO e conversão.
- Use fotos consistentes (mesma proporção e qualidade).
- Não é necessário usar `/admin/` do Django para o catálogo.

## Mercado Pago (gestor)
- Credenciais em `.env`: ACCESS_TOKEN, PUBLIC_KEY, WEBHOOK_SECRET.
- Validar: `python manage.py check_mercadopago`
- Testes: ver `TESTING_MERCADOPAGO.md`
