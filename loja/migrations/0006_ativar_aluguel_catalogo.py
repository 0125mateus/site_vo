from decimal import Decimal

from django.db import migrations


def ativar_aluguel_catalogo(apps, schema_editor):
    Produto = apps.get_model('loja', 'Produto')
    for p in Produto.objects.all():
        changed = False
        if p.estoque and not p.estoque_aluguel:
            p.estoque_aluguel = max(1, p.estoque)
            changed = True
        if p.preco and (not p.preco_aluguel or p.preco_aluguel == 0):
            p.preco_aluguel = (p.preco * Decimal('0.15')).quantize(Decimal('0.01'))
            changed = True
        if not p.disponivel_aluguel:
            p.disponivel_aluguel = True
            changed = True
        if not p.disponivel_venda:
            p.disponivel_venda = True
            changed = True
        if changed:
            p.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0005_venda_aluguel'),
    ]

    operations = [
        migrations.RunPython(ativar_aluguel_catalogo, noop),
    ]
