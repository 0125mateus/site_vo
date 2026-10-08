import uuid
from pathlib import Path

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import slugify

User = get_user_model()


def _nome_arquivo_seguro(filename: str) -> str:
    nome = Path(str(filename).replace('\\', '/')).name
    stem = slugify(Path(nome).stem, allow_unicode=False) or 'arquivo'
    ext = Path(nome).suffix.lower()[:12]
    return f'{stem[:80]}{ext}'


def produto_imagem_upload_path(instance, filename):
    folder = instance.pk or uuid.uuid4().hex
    return f'produtos/{folder}/{_nome_arquivo_seguro(filename)}'


def produto_arquivo_upload_path(instance, filename):
    folder = instance.pk or uuid.uuid4().hex
    return f'produtos/{folder}/arquivos/{_nome_arquivo_seguro(filename)}'


class ModalidadeComercial(models.TextChoices):
    VENDA = 'venda', 'Venda'
    ALUGUEL = 'aluguel', 'Aluguel'
    ASSISTIR = 'assistir', 'Assistir online'


class Produto(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    imagem = models.ImageField(
        upload_to=produto_imagem_upload_path,
        blank=True,
        null=True,
        max_length=500,
        help_text='Capa (JPG, PNG ou WebP).',
    )
    arquivo = models.FileField(
        upload_to=produto_arquivo_upload_path,
        blank=True,
        null=True,
        max_length=500,
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
    disponivel_assistir = models.BooleanField('disponível para assistir online', default=False)
    preco_assistir = models.DecimalField(
        'preço para assistir',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Valor cobrado para assistir o filme online.',
    )
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
        if modalidade == ModalidadeComercial.ASSISTIR:
            return self.preco_assistir
        return self.preco

    def estoque_para(self, modalidade: str) -> int:
        if modalidade == ModalidadeComercial.ALUGUEL:
            return self.estoque_aluguel
        if modalidade == ModalidadeComercial.ASSISTIR:
            return 1
        return self.estoque

    def disponivel_para(self, modalidade: str) -> bool:
        if not self.ativo:
            return False
        if modalidade == ModalidadeComercial.ALUGUEL:
            return self.disponivel_aluguel and self.estoque_aluguel > 0 and self.preco_aluguel > 0
        if modalidade == ModalidadeComercial.ASSISTIR:
            return self.disponivel_assistir and self.preco_assistir > 0
        return self.disponivel_venda and self.estoque > 0 and self.preco > 0

    @property
    def pode_assistir(self) -> bool:
        return self.disponivel_para(ModalidadeComercial.ASSISTIR)

    @property
    def pode_comprar(self) -> bool:
        return self.disponivel_para(ModalidadeComercial.VENDA)

    def rotulo_modalidade(self, modalidade: str) -> str:
        if modalidade == ModalidadeComercial.VENDA and self.ficha_midia():
            return 'DVD físico'
        return dict(ModalidadeComercial.choices).get(modalidade, modalidade)

    def ficha_midia(self):
        """A ficha de filme, mesmo quando a prateleira entrega o produto genérico."""
        if isinstance(self, MidiaAudiovisual):
            return self
        try:
            return self.midiaaudiovisual
        except MidiaAudiovisual.DoesNotExist:
            return None


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
    return f'produtos/{folder}/trailers/{_nome_arquivo_seguro(filename)}'


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
        max_length=500,
        help_text='Prévia em vídeo do PC (MP4, WebM…).',
    )
    trailer_url = models.URLField(
        'trailer (YouTube/Vimeo)',
        blank=True,
        help_text='Opcional: link do YouTube ou Vimeo se preferir não enviar arquivo.',
    )
    filme_url = models.URLField(
        'link do filme completo',
        blank=True,
        max_length=500,
        help_text='YouTube não listado, Vimeo ou Google Drive. Só quem pagou para assistir vê.',
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
        return embed_de_video(self.trailer_url)

    @property
    def filme_embed_url(self) -> str:
        return embed_de_video(self.filme_url)

    @property
    def tem_filme_online(self) -> bool:
        return bool(self.filme_url) or bool(self.arquivo)


def embed_de_video(url) -> str:
    """YouTube, Vimeo ou Google Drive viram endereço de player; outros links passam como vieram."""
    import re

    url = (url or '').strip()
    if not url:
        return ''
    yt = re.search(
        r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{6,})',
        url,
    )
    if yt:
        # youtube-nocookie + rel=0; Referrer-Policy do site completa a config do player
        return f'https://www.youtube-nocookie.com/embed/{yt.group(1)}?rel=0'
    vm = re.search(r'vimeo\.com/(?:video/)?(\d+)', url)
    if vm:
        return f'https://player.vimeo.com/video/{vm.group(1)}'
    drive = re.search(r'drive\.google\.com/(?:file/d/|open\?id=)([A-Za-z0-9_-]{10,})', url)
    if drive:
        return f'https://drive.google.com/file/d/{drive.group(1)}/preview'
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
    desconto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Descontos de combo, clube etc.',
    )
    plano_clube = models.ForeignKey(
        'PlanoClube',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos',
    )
    mercadopago_preference_id = models.CharField(max_length=255, null=True, blank=True)

    entrega_nome = models.CharField('nome de quem recebe', max_length=120, blank=True)
    entrega_telefone = models.CharField('telefone', max_length=30, blank=True)
    entrega_cep = models.CharField('CEP', max_length=9, blank=True)
    entrega_logradouro = models.CharField('rua', max_length=200, blank=True)
    entrega_numero = models.CharField('número', max_length=20, blank=True)
    entrega_complemento = models.CharField('complemento', max_length=100, blank=True)
    entrega_bairro = models.CharField('bairro', max_length=100, blank=True)
    entrega_cidade = models.CharField('cidade', max_length=100, blank=True)
    entrega_uf = models.CharField('estado (UF)', max_length=2, blank=True)

    class StatusEntrega(models.TextChoices):
        PREPARANDO = 'preparando', 'Preparando o envio'
        ENVIADO = 'enviado', 'Enviado'
        SAIU = 'saiu_para_entrega', 'Saiu para entrega'
        ENTREGUE = 'entregue', 'Entregue'

    status_entrega = models.CharField(
        'andamento da entrega', max_length=20, choices=StatusEntrega.choices, blank=True,
    )
    transportadora = models.CharField(max_length=60, blank=True)
    codigo_rastreio = models.CharField('código de rastreio', max_length=60, blank=True)
    link_rastreio = models.URLField('link de rastreio', max_length=500, blank=True)

    CAMPOS_ENTREGA = (
        'entrega_nome', 'entrega_telefone', 'entrega_cep', 'entrega_logradouro',
        'entrega_numero', 'entrega_complemento', 'entrega_bairro', 'entrega_cidade', 'entrega_uf',
    )

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f'Pedido #{self.pk} — {self.cliente}'

    @property
    def precisa_entrega(self) -> bool:
        return self.itens.filter(modalidade=ModalidadeComercial.VENDA).exists()

    @property
    def tem_endereco(self) -> bool:
        return all(getattr(self, campo) for campo in (
            'entrega_nome', 'entrega_cep', 'entrega_logradouro', 'entrega_numero',
            'entrega_bairro', 'entrega_cidade', 'entrega_uf',
        ))

    @property
    def url_rastreio(self) -> str:
        if self.link_rastreio:
            return self.link_rastreio
        if self.codigo_rastreio and 'correios' in self.transportadora.lower():
            return 'https://rastreamento.correios.com.br/app/index.php'
        return ''

    def registrar_evento(self, etapa: str, mensagem: str = ''):
        return EventoPedido.objects.create(pedido=self, etapa=etapa, mensagem=mensagem[:255])

    def linha_do_tempo(self) -> list:
        """Etapas do pedido para o cliente acompanhar, como nas lojas grandes."""
        datas = {}
        mensagens = {}
        for evento in self.eventos.all():
            datas.setdefault(evento.etapa, evento.criado_em)
            if evento.mensagem:
                mensagens[evento.etapa] = evento.mensagem

        etapas = [('pedido', 'Pedido feito', self.criado_em)]
        if self.status in (self.STATUS_RECUSADO, self.STATUS_CANCELADO):
            etapas.append((self.status, self.get_status_display(), datas.get(self.status)))
            concluidas = len(etapas)
        else:
            aprovado = self.status == self.STATUS_APROVADO
            etapas.append(('pagamento', 'Pagamento confirmado', datas.get('pagamento')))
            concluidas = 2 if aprovado else 1
            if self.precisa_entrega:
                ordem = [valor for valor, _ in self.StatusEntrega.choices]
                for valor, rotulo in self.StatusEntrega.choices:
                    etapas.append((valor, rotulo, datas.get(valor)))
                if aprovado and self.status_entrega:
                    concluidas = 3 + ordem.index(self.status_entrega)
            else:
                etapas.append(('liberado', 'Filme liberado na Biblioteca', datas.get('pagamento')))
                if aprovado:
                    concluidas = 3

        return [
            {
                'chave': chave,
                'titulo': titulo,
                'data': data,
                'mensagem': mensagens.get(chave, ''),
                'feita': indice < concluidas,
                'atual': indice == concluidas - 1,
            }
            for indice, (chave, titulo, data) in enumerate(etapas)
        ]

    @property
    def resumo_acompanhamento(self) -> str:
        if self.status != self.STATUS_APROVADO:
            return self.get_status_display()
        if not self.precisa_entrega:
            return 'Filme liberado'
        return self.get_status_entrega_display() or 'Pagamento confirmado'

    @property
    def endereco_entrega(self) -> str:
        if not self.tem_endereco:
            return ''
        linha = f'{self.entrega_logradouro}, {self.entrega_numero}'
        if self.entrega_complemento:
            linha += f' — {self.entrega_complemento}'
        return (
            f'{linha} · {self.entrega_bairro} · {self.entrega_cidade}/{self.entrega_uf} · '
            f'CEP {self.entrega_cep}'
        )

    def recalcular_valor_total(self):
        subtotal = sum(
            (item.preco_unitario * item.quantidade for item in self.itens.all()),
            Decimal('0.00'),
        )
        if self.plano_clube_id:
            subtotal += self.plano_clube.preco_mensal
        self.valor_total = max(Decimal('0.00'), subtotal - self.desconto)
        self.save(update_fields=['valor_total'])
        return self.valor_total


class EventoPedido(models.Model):
    """Histórico do pedido: pagamento confirmado, enviado, entregue…"""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='eventos')
    etapa = models.CharField(max_length=20)
    mensagem = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em', 'pk']

    def __str__(self):
        return f'Pedido #{self.pedido_id} — {self.rotulo}'

    @property
    def rotulo(self) -> str:
        rotulos = {
            'pagamento': 'Pagamento confirmado',
            Pedido.STATUS_RECUSADO: 'Pagamento recusado',
            Pedido.STATUS_CANCELADO: 'Cancelado',
            **dict(Pedido.StatusEntrega.choices),
        }
        return rotulos.get(self.etapa, self.etapa)


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
        return f'{self.quantidade}x {self.produto.titulo} ({self.modalidade_label})'

    @property
    def modalidade_label(self) -> str:
        return self.produto.rotulo_modalidade(self.modalidade)

    @property
    def is_assistir(self) -> bool:
        return self.modalidade == ModalidadeComercial.ASSISTIR

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
        if self.modalidade == ModalidadeComercial.ASSISTIR:
            return True
        if self.modalidade == ModalidadeComercial.VENDA:
            # Comprar o DVD físico não libera o filme online; para isso existe "Assistir online".
            return not self.produto.ficha_midia()
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


class PlanoClube(models.Model):
    titulo = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    preco_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    desconto_extra_percent = models.PositiveIntegerField(
        default=5,
        help_text='Desconto adicional em compras (%) para assinantes.',
    )
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordem', 'preco_mensal']
        verbose_name = 'Plano do clube'
        verbose_name_plural = 'Planos do clube'

    def __str__(self):
        return self.titulo


class AssinaturaClube(models.Model):
    STATUS_ATIVA = 'ativa'
    STATUS_EXPIRADA = 'expirada'
    STATUS_CANCELADA = 'cancelada'

    STATUS_CHOICES = [
        (STATUS_ATIVA, 'Ativa'),
        (STATUS_EXPIRADA, 'Expirada'),
        (STATUS_CANCELADA, 'Cancelada'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assinaturas_clube',
    )
    plano = models.ForeignKey(
        PlanoClube,
        on_delete=models.PROTECT,
        related_name='assinaturas',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ATIVA)
    valido_ate = models.DateField()
    ultimo_pedido = models.ForeignKey(
        Pedido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assinaturas_clube',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Assinatura do clube'
        verbose_name_plural = 'Assinaturas do clube'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'plano'],
                name='uniq_assinatura_usuario_plano',
            ),
        ]

    def __str__(self):
        return f'{self.usuario} — {self.plano.titulo}'

    @property
    def ativa(self) -> bool:
        from django.utils import timezone
        return (
            self.status == self.STATUS_ATIVA
            and self.valido_ate >= timezone.localdate()
        )


class Favorito(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favoritos',
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='favoritado_por',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favorito'
        verbose_name_plural = 'Favoritos'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'produto'],
                name='uniq_favorito_usuario_produto',
            ),
        ]
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.usuario} ♥ {self.produto.titulo}'


class Avaliacao(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avaliacoes',
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='avaliacoes',
    )
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        ordering = ['-criado_em']
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'produto'],
                name='uniq_avaliacao_usuario_produto',
            ),
            models.CheckConstraint(
                check=models.Q(nota__gte=1) & models.Q(nota__lte=5),
                name='avaliacao_nota_1_a_5',
            ),
        ]

    def __str__(self):
        return f'{self.produto.titulo} — {self.nota}★'


class InscricaoNewsletter(models.Model):
    email = models.EmailField(unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Inscrição na newsletter'
        verbose_name_plural = 'Inscrições na newsletter'
        ordering = ['-criado_em']

    def __str__(self):
        return self.email


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


class ConfiguracaoPix(models.Model):
    """Chave Pix da própria loja. Quando preenchida, o checkout gera o QR Code com ela."""

    class TipoChave(models.TextChoices):
        CPF = 'cpf', 'CPF'
        CNPJ = 'cnpj', 'CNPJ'
        TELEFONE = 'telefone', 'Celular'
        EMAIL = 'email', 'E-mail'
        ALEATORIA = 'aleatoria', 'Chave aleatória'

    tipo_chave = models.CharField('tipo da chave', max_length=10, choices=TipoChave.choices)
    chave = models.CharField('chave Pix', max_length=77)
    nome_recebedor = models.CharField(
        'nome de quem recebe', max_length=25,
        help_text='Como aparece no banco do cliente. Até 25 letras.',
    )
    cidade = models.CharField('cidade', max_length=15, help_text='Até 15 letras.')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pix da loja'
        verbose_name_plural = 'Pix da loja'

    def __str__(self):
        return f'{self.get_tipo_chave_display()}: {self.chave}'

    @classmethod
    def atual(cls):
        config = cls.objects.order_by('-atualizado_em').first()
        return config if config and config.chave and config.nome_recebedor and config.cidade else None
