from django.contrib import admin
from django.utils.html import format_html

from .models import ItemPedido, Livro, MidiaAudiovisual, Musica, Pagamento, Pedido, Produto


class ImagemPreviewMixin:
    readonly_fields = ('imagem_preview',)

    @admin.display(description='Prévia')
    def imagem_preview(self, obj):
        if obj.imagem:
            return format_html(
                '<img src="{}" style="max-height:120px;border-radius:8px;" alt="">',
                obj.imagem.url,
            )
        return '—'


@admin.register(Produto)
class ProdutoAdmin(ImagemPreviewMixin, admin.ModelAdmin):
    list_display = ('titulo', 'preco', 'estoque', 'ativo', 'tem_imagem', 'tem_arquivo', 'criado_em')
    list_filter = ('ativo',)
    search_fields = ('titulo', 'descricao')
    fields = (
        'titulo', 'descricao', 'imagem', 'imagem_preview',
        'arquivo', 'preco', 'estoque', 'ativo',
    )

    @admin.display(boolean=True, description='Imagem')
    def tem_imagem(self, obj):
        return bool(obj.imagem)

    @admin.display(boolean=True, description='Arquivo')
    def tem_arquivo(self, obj):
        return bool(obj.arquivo)


@admin.register(Musica)
class MusicaAdmin(ImagemPreviewMixin, admin.ModelAdmin):
    list_display = ('titulo', 'artista', 'formato', 'preco', 'estoque', 'ativo', 'tem_imagem', 'tem_arquivo')
    search_fields = ('titulo', 'artista')
    fields = (
        'titulo', 'descricao', 'imagem', 'imagem_preview', 'arquivo',
        'disponivel_venda', 'preco', 'estoque',
        'disponivel_aluguel', 'preco_aluguel', 'dias_aluguel', 'estoque_aluguel',
        'ativo', 'artista', 'formato',
    )

    @admin.display(boolean=True, description='Imagem')
    def tem_imagem(self, obj):
        return bool(obj.imagem)

    @admin.display(boolean=True, description='Arquivo')
    def tem_arquivo(self, obj):
        return bool(obj.arquivo)


@admin.register(Livro)
class LivroAdmin(ImagemPreviewMixin, admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'isbn', 'preco', 'estoque', 'ativo', 'tem_imagem', 'tem_arquivo')
    search_fields = ('titulo', 'autor', 'isbn')
    fields = (
        'titulo', 'descricao', 'imagem', 'imagem_preview', 'arquivo',
        'disponivel_venda', 'preco', 'estoque',
        'disponivel_aluguel', 'preco_aluguel', 'dias_aluguel', 'estoque_aluguel',
        'ativo', 'autor', 'isbn',
    )

    @admin.display(boolean=True, description='Imagem')
    def tem_imagem(self, obj):
        return bool(obj.imagem)

    @admin.display(boolean=True, description='Arquivo')
    def tem_arquivo(self, obj):
        return bool(obj.arquivo)


@admin.register(MidiaAudiovisual)
class MidiaAudiovisualAdmin(ImagemPreviewMixin, admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'diretor', 'ano', 'preco', 'estoque', 'ativo', 'tem_imagem', 'tem_arquivo')
    list_filter = ('tipo', 'ativo')
    search_fields = ('titulo', 'diretor')
    fields = (
        'titulo', 'tipo', 'diretor', 'ano', 'duracao_min', 'descricao',
        'imagem', 'imagem_preview', 'trailer', 'trailer_url', 'arquivo',
        'disponivel_venda', 'preco', 'estoque',
        'disponivel_aluguel', 'preco_aluguel', 'dias_aluguel', 'estoque_aluguel',
        'ativo',
    )

    @admin.display(boolean=True, description='Imagem')
    def tem_imagem(self, obj):
        return bool(obj.imagem)

    @admin.display(boolean=True, description='Arquivo')
    def tem_arquivo(self, obj):
        return bool(obj.arquivo)


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ('produto', 'quantidade', 'preco_unitario')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cliente',
        'status',
        'valor_total',
        'mercadopago_preference_id',
        'criado_em',
    )
    list_filter = ('status', 'criado_em')
    search_fields = ('cliente__username', 'cliente__email', 'mercadopago_preference_id')
    readonly_fields = ('criado_em', 'valor_total')
    inlines = [ItemPedidoInline]


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = (
        'pedido',
        'mercadopago_payment_id',
        'status',
        'metodo_pagamento',
        'valor',
        'atualizado_em',
    )
    list_filter = ('status', 'metodo_pagamento')
    search_fields = ('mercadopago_payment_id', 'pedido__id')
