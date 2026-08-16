from decimal import Decimal

from django.core.management.base import BaseCommand

from loja.models import Livro, Musica, Produto


class Command(BaseCommand):
    help = 'Cria produtos de demonstração para a loja'

    def handle(self, *args, **options):
        if Produto.objects.exists():
            self.stdout.write('Produtos já existem — nada a fazer.')
            return

        Musica.objects.create(
            titulo='Abbey Road',
            descricao='Edição remasterizada em vinil.',
            preco=Decimal('189.90'),
            estoque=12,
            artista='The Beatles',
            formato='vinil',
        )
        Musica.objects.create(
            titulo='Kind of Blue',
            descricao='Jazz clássico em vinil 180g.',
            preco=Decimal('159.90'),
            estoque=8,
            artista='Miles Davis',
            formato='vinil',
        )
        Livro.objects.create(
            titulo='O Pequeno Príncipe',
            descricao='Edição de bolso com ilustrações originais.',
            preco=Decimal('29.90'),
            estoque=25,
            autor='Antoine de Saint-Exupéry',
            isbn='978-8532650601',
        )
        Livro.objects.create(
            titulo='1984',
            descricao='Distopia atemporal de George Orwell.',
            preco=Decimal('34.90'),
            estoque=18,
            autor='George Orwell',
            isbn='978-8535914849',
        )

        self.stdout.write(self.style.SUCCESS('Produtos de demonstração criados com sucesso.'))
