import loja.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0011_avaliacao_newsletter'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produto',
            name='arquivo',
            field=models.FileField(
                blank=True,
                help_text='Arquivo digital opcional (MP3, FLAC, MP4, MKV, PDF…).',
                max_length=500,
                null=True,
                upload_to=loja.models.produto_arquivo_upload_path,
            ),
        ),
        migrations.AlterField(
            model_name='produto',
            name='imagem',
            field=models.ImageField(
                blank=True,
                help_text='Capa (JPG, PNG ou WebP).',
                max_length=500,
                null=True,
                upload_to=loja.models.produto_imagem_upload_path,
            ),
        ),
        migrations.AlterField(
            model_name='midiaaudiovisual',
            name='trailer',
            field=models.FileField(
                blank=True,
                help_text='Prévia em vídeo do PC (MP4, WebM…).',
                max_length=500,
                null=True,
                upload_to=loja.models.produto_trailer_upload_path,
                verbose_name='trailer (arquivo)',
            ),
        ),
    ]
