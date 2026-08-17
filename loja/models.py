import uuid

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


def produto_imagem_upload_path(instance, filename):
    folder = instance.pk or uuid.uuid4().hex
    return f'produtos/{folder}/{filename}'


def produto_arquivo_upload_path(instance, filename):
    folder = instance.pk or uuid.uuid4().hex
    return f'produtos/{folder}/arquivos/{filename}'


class ModalidadeComercial(models.TextChoices):
    VENDA = 'venda', 'Venda'
    ALUGUEL = 'aluguel', 'Aluguel'


class Produto(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(
        upload_to=produto_imagem_upload_path,
        blank=True,
        null=True,
        help_text='Capa (JPG, PNG ou WebP).',
    )
    arquivo = models.FileField(
        upload_to=produto_arquivo_upload_path,
        blank=True,
        null=True,
        help_text='Arquivo digital opcional (MP3, FLAC, MP4, MKV, PDF…).',
    )
    preco = models.DecimalField('preço de venda', max_digits=10, decimal_places=2)
    preco_aluguel = models.DecimalField(
        'preço do aluguel',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Valor cobrado por período de aluguel.',
    )
    dias_aluguel = models.PositiveIntegerField(
        'dias de aluguel',
        default=7,
        help_text='Quantidade de dias inclusos no preço do aluguel.',
    )
    disponivel_venda = models.BooleanField('disponível para venda', default=True)
    disponivel_aluguel = models.BooleanField('disponível para aluguel', default=False)
    estoque = models.PositiveIntegerField('estoque venda', default=0)
    estoque_aluguel = models.PositiveIntegerField('estoque aluguel', default=0)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['titulo']

    def __str__(self):
        return self.titulo

    @property
    def tem_arquivo(self) -> bool:
        return bool(self.arquivo)

    def preco_para(self, modalidade: str) -> Decimal:
        if modalidade == ModalidadeComercial.ALUGUEL:
            return self.preco_aluguel
        return self.preco

    def estoque_para(self, modalidade: str) -> int:
        if modalidade == ModalidadeComercial.ALUGUEL:
            return self.estoque_aluguel
        return self.estoque

    def disponivel_para(self, modalidade: str) -> bool:
        if not self.ativo:
            return False
        if modalidade == ModalidadeComercial.ALUGUEL:
            return self.disponivel_aluguel and self.estoque_aluguel > 0 and self.preco_aluguel > 0
        return self.disponivel_venda and self.estoque > 0 and self.preco > 0


class Musica(Produto):
    artista = models.CharField(max_length=200)
    formato = models.CharField(max_length=50, default='vinil')

    class Meta:
        verbose_name = 'Música'
        verbose_name_plural = 'Músicas'

    def __str__(self):
        return f'{self.artista} — {self.titulo}'


class Livro(Produto):
    autor = models.CharField(max_length=200)
    isbn = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'Livro'
        verbose_name_plural = 'Livros'

    def __str__(self):
        return f'{self.titulo} — {self.autor}'


def produto_trailer_upload_path(instance, filename):
    folder = instance.pk or uuid.uuid4().hex
    return f'produtos/{folder}/trailers/{filename}'


class MidiaAudiovisual(Produto):
    class Tipo(models.TextChoices):
        FILME = 'filme', 'Filme'
        VIDEO = 'video', 'Vídeo'
        DVD = 'dvd', 'DVD'
        BLURAY = 'bluray', 'Blu-ray'

    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.DVD)
    diretor = models.CharField(max_length=200, blank=True)
    ano = models.PositiveIntegerField(null=True, blank=True)
    duracao_min = models.PositiveIntegerField(
        'duração (min)',
        null=True,
        blank=True,
    )
    trailer = models.FileField(
        'trailer (arquivo)',
        upload_to=produto_trailer_upload_path,
        blank=True,
        null=True,
        help_text='Prévia em vídeo do PC (MP4, WebM…).',
    )
    trailer_url = models.URLField(
        'trailer (YouTube/Vimeo)',
        blank=True,
        help_text='Opcional: link do YouTube ou Vimeo se preferir não enviar arquivo.',
    )

    class Meta:
        verbose_name = 'Mídia audiovisual'
        verbose_name_plural = 'Mídias audiovisuais'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.titulo}'

    @property
    def tem_trailer(self) -> bool:
        return bool(self.trailer) or bool(self.trailer_url)

    @property
    def trailer_embed_url(self) -> str:
        """Converte YouTube/Vimeo em URL de embed; vazio se for arquivo local."""
        url = (self.trailer_url or '').strip()
        if not url:
            return ''
        import re
        yt = re.search(
            r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})',
            url,
        )
        if yt:
            # youtube-nocookie + rel=0; Referrer-Policy do site completa a config do player
            return f'https://www.youtube-nocookie.com/embed/{yt.group(1)}?rel=0'
        vm = re.search(r'vimeo\.com/(?:video/)?(\d+)', url)
        if vm:
            return f'https://player.vimeo.com/video/{vm.group(1)}'
        return url


class Pedido(models.Model):
    STATUS_AGUARDANDO = 'aguardando_pagamento'
    STATUS_APROVADO = 'aprovado'
    STATUS_RECUSADO = 'recusado'
    STATUS_EM_ANALISE = 'em_analise'
    STATUS_CANCELADO = 'cancelado'

    STATUS_CHOICES = [
        (STATUS_AGUARDANDO, 'Aguardando pagamento'),
        (STATUS_APROVADO, 'Aprovado'),
        (STATUS_RECUSADO, 'Recusado'),
        (STATUS_EM_ANALISE, 'Em análise'),
        (STATUS_CANCELADO, 'Cancelado'),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pedidos',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_AGUARDANDO,
    )
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    mercadopago_preference_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f'Pedido #{self.pk} — {self.cliente}'

    def recalcular_valor_total(self):
        total = sum(
            (item.preco_unitario * item.quantidade for item in self.itens.all()),
            Decimal('0.00'),
        )
        self.valor_total = total
        self.save(update_fields=['valor_total'])
        return total


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    modalidade = models.CharField(
        max_length=20,
        choices=ModalidadeComercial.choices,
        default=ModalidadeComercial.VENDA,
    )
    quantidade = models.PositiveIntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    dias_aluguel = models.PositiveIntegerField(null=True, blank=True)
    data_devolucao = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Item do pedido'
        verbose_name_plural = 'Itens do pedido'

    def __str__(self):
        return f'{self.quantidade}x {self.produto.titulo} ({self.get_modalidade_display()})'

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade

    @property
    def is_aluguel(self):
        return self.modalidade == ModalidadeComercial.ALUGUEL

    @property
    def pedido_aprovado(self) -> bool:
        return self.pedido.status == Pedido.STATUS_APROVADO

    @property
    def aluguel_ativo(self) -> bool:
        if not self.is_aluguel or not self.pedido_aprovado:
            return False
        if not self.data_devolucao:
            return True
        from django.utils import timezone
        return self.data_devolucao >= timezone.localdate()

    @property
    def dias_restantes(self) -> int | None:
        if not self.is_aluguel or not self.data_devolucao:
            return None
        from django.utils import timezone
        return max(0, (self.data_devolucao - timezone.localdate()).days)

    @property
    def acesso_liberado(self) -> bool:
        if not self.pedido_aprovado:
            return False
        if self.modalidade == ModalidadeComercial.VENDA:
            return True
        return self.aluguel_ativo


class Pagamento(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='pagamento')
    mercadopago_payment_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    status = models.CharField(max_length=50)
    metodo_pagamento = models.CharField(max_length=50, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'

    def __str__(self):
        return f'Pagamento do pedido #{self.pedido_id} — {self.status}'


class ProgressoReproducao(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progressos_reproducao',
    )
    item_pedido = models.ForeignKey(
        ItemPedido,
        on_delete=models.CASCADE,
        related_name='progressos',
    )
    segundos = models.PositiveIntegerField(default=0)
    duracao_segundos = models.PositiveIntegerField(null=True, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Progresso de reprodução'
        verbose_name_plural = 'Progressos de reprodução'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'item_pedido'],
                name='uniq_progresso_usuario_item',
            ),
        ]

    def __str__(self):
        return f'{self.usuario} — item #{self.item_pedido_id} @ {self.segundos}s'

    @property
    def percentual(self) -> int:
        if not self.duracao_segundos:
            return 0
        return min(100, round(100 * self.segundos / self.duracao_segundos))

    @property
    def em_andamento(self) -> bool:
        if not self.duracao_segundos or self.duracao_segundos <= 0:
            return self.segundos > 0
        return 0 < self.segundos < (self.duracao_segundos - 15)


class FraseTreinoAssistente(models.Model):
    AUDIENCIA_CLIENTE = 'cliente'
    AUDIENCIA_GESTOR = 'gestor'
    AUDIENCIA_CHOICES = [
        (AUDIENCIA_CLIENTE, 'Cliente (loja)'),
        (AUDIENCIA_GESTOR, 'Gestor (painel)'),
    ]

    audiencia = models.CharField(max_length=10, choices=AUDIENCIA_CHOICES)
    intencao = models.CharField(max_length=40)
    texto = models.CharField(max_length=300)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Frase de treino do assistente'
        verbose_name_plural = 'Frases de treino do assistente'
        ordering = ['audiencia', 'intencao', 'texto']

    def __str__(self):
        return f'{self.texto[:50]}…' if len(self.texto) > 50 else self.texto

    def get_intencao_label(self):
        from .assistant_intent import INTENT_LABELS_CLIENTE, INTENT_LABELS_GESTOR

        labels = INTENT_LABELS_GESTOR if self.audiencia == self.AUDIENCIA_GESTOR else INTENT_LABELS_CLIENTE
        return labels.get(self.intencao, self.intencao)
